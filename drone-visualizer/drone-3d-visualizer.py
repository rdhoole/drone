from direct.showbase.ShowBase import ShowBase
from panda3d.core import TextNode
from math import pi, sin, cos
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
import socket
from time import sleep
from sys import exit
import gltf

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect(("192.168.2.1", 12121))
        except:
            print("Failed to connected to server.")

        # patch gltf to loader...
        gltf.patch_loader(self.loader)
        
        # Load the environment model.
        #self.scene = self.loader.loadModel("models/environment")
        self.drone = self.loader.loadModel("drone-visualizer/drone-visualizer.glb")

        # onscreen text
        self.telemetry_altitude = OnscreenText(text='Altitude: ?', pos=(-1, 0.05), scale=0.07, mayChange=True, align=TextNode.ALeft)
        self.telemetry_heading = OnscreenText(text='Heading: ?', pos=(-1, -0.05), scale=0.07, mayChange=True, align=TextNode.ALeft)
        self.telemetry_pitch = OnscreenText(text='Pitch: ?', pos=(0.4, 0), scale=0.07, mayChange=True, align=TextNode.ALeft)
        self.telemetry_roll = OnscreenText(text='Roll: ?', pos=(-0.15, 0.2), scale=0.07, mayChange=True, align=TextNode.ALeft)

        self.rot = "Unknown!"
        self.loc = "Unknown!"
        self.altitude = "~"
        self.heading  = "~"
        self.roll     = "0"
        self.pitch    = "0"

        # Reparent the model to render.
        #self.scene.reparentTo(self.render)
        #self.camera.reparentTo(self.drone)
        self.drone.reparentTo(self.render)
        # Apply scale and position transforms on the model.
        #self.scene.setScale(0.25, 0.25, 0.25)
        #self.scene.setPos(-8, 42, 0)

        self.drone.setScale(1, 1, 1)
        self.drone.setPos(0, 0, 0)

        # Add the spinCameraTask procedure to the task manager.
        self.taskMgr.add(self.CameraTask, "CameraTask")
        self.taskMgr.add(self.droneMovement, "DroneMovement")
        self.taskMgr.add(self.droneTelemetryText, "DroneTelemetryText")
        
    # Define a procedure to move the camera.
    def CameraTask(self, task):
        self.camera.setPos(0 + self.drone.getX(), \
                           -5 + self.drone.getY(), \
                           0 + self.drone.getZ())
        self.camera.setHpr(0,
                           self.drone.getP(),
                           0)
        self.camera.lookAt(self.drone.getPos())
        return Task.cont

    def droneTelemetryText(self, task):
        self.telemetry_altitude.setText('Altitude: ' + self.altitude + 'M')
        self.telemetry_heading.setText('Heading: ' + self.heading)
        self.telemetry_pitch.setText('Pitch: {:3.0f}\N{DEGREE SIGN}'.format(float(self.pitch)*-1))
        self.telemetry_roll.setText('Roll: {:3.0f}\N{DEGREE SIGN}'.format(float(self.roll)))
        return Task.cont
        
    def droneMovement(self, task):
        try:
            data = self.s.recv(1048).decode().rstrip()
            self.rot = str(data.split(":")[0])
            self.loc = str(data.split(":")[1])

            self.altitude = self.loc.split(" ")[2].split("\n")[0]
            self.heading  = self.rot.split(" ")[2]
            self.roll     = self.rot.split(" ")[0]
            self.pitch    = self.rot.split(" ")[1]

            
            x, y, z = self.rot.split(" ")
            self.drone.setHpr(0, \
                              (float(y)*-1), \
                              float(x))
            x, y, z = self.loc.split(" ")
            self.drone.setPos(float(x), \
                              float(y), \
                              0)#float(z))
            
        except:
            print(e)
            pass
        
        finally:
            return Task.cont
        
app = MyApp()
app.run()
