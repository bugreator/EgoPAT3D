import numpy as np
import warnings
import os
import open3d as o3d
import cv2
from torch.utils.data import Dataset
import re
from functools import reduce

def farthest_point_sample(point, npoint):
    """
    Input:
        xyz: pointcloud data, [N, D]
        npoint: number of samples
    Return:
        centroids: sampled pointcloud index, [npoint, D]
    """
    N, D = point.shape
    xyz = point[:,:3]
    centroids = np.zeros((npoint,))
    distance = np.ones((N,)) * 1e10
    farthest = np.random.randint(0, N)
    for i in range(npoint):
        centroids[i] = farthest
        centroid = xyz[farthest, :]
        dist = np.sum((xyz - centroid) ** 2, -1)
        mask = dist < distance
        distance[mask] = dist[mask]
        farthest = np.argmax(distance, -1)
    point = point[centroids.astype(np.int32)]
    return point

def tryint(s):                    
    try:
        return int(s)
    except ValueError:
        return s

def str2int(v_str):            
    return [tryint(sub_str) for sub_str in re.split('([0-9]+)', v_str)]

class valittDataLoader(Dataset):
    def __init__(self, root,num):
        self.root = root
        self.scenepath=os.path.join(root,'sequences')
        self.gtpath=os.path.join(root,'annovalidate')
        self.num=num
        self.numscene=os.listdir(self.gtpath)
        self.indexlist=[]
        self.maxclip=0

        for scene in self.numscene:
            
            recordpath=os.path.join(self.gtpath,scene)
            recordname=os.listdir(recordpath)
            recordname.sort(key=str2int)
            
            for txtnum in recordname:
                txtpath=os.path.join(recordpath,txtnum)
                f=open(txtpath)
                data=f.readlines()
                for linenum in range(len(data)):
                    line=data[linenum].strip('\n').split(',')
                    if len(line)==9:
                        for ran in range(2):
                            if ran==0:
                                self.indexlist.append([scene,txtnum[:-4],line[0],line[1],line[3:6]])
                                self.maxclip=max(self.maxclip,int(int(line[1])-int(line[0])))
                            else:
                                self.indexlist.append([scene,txtnum[:-4],line[1],line[2],line[6:]])
                                self.maxclip=max(self.maxclip,int(int(line[2])-int(line[1])))
                                
                    elif len(line)==13:
                        for ran in range(3):
                            if ran==0:
                                self.indexlist.append([scene,txtnum[:-4],line[0],line[1],line[4:7]])
                                self.maxclip=max(self.maxclip,int(int(line[1])-int(line[0])))
                            elif ran==1:
                                self.indexlist.append([scene,txtnum[:-4],line[1],line[2],line[7:10]])
                                self.maxclip=max(self.maxclip,int(int(line[2])-int(line[1])))
                            else:
                                self.indexlist.append([scene,txtnum[:-4],line[2],line[3],line[10:]])
                                self.maxclip=max(self.maxclip,int(int(line[3])-int(line[2])))
                                
                    elif len(line)==5:
                        for ran in range(1):
                            self.indexlist.append([scene,txtnum[:-4],line[0],line[1],line[2:]])
                            self.maxclip=max(self.maxclip,int(int(line[1])-int(line[0])))
                    else:
                        print('cliperror')
                f.close()
                
        self.length=len(self.indexlist)
            
                    
    def getimudata(self,imupath,start):
        imudata={}
        f=open(imupath,'r')
        alldata=f.readlines()
        for line in alldata:
            data=line.strip('\n').split(',')
            if float(data[0])>0.03*(start-1) and float(data[0])<0.03*(start):
                imudata[data[0]]=np.array([float(data[1]),float(data[2]),float(data[3]),\
                    float(data[4]),float(data[5]),float(data[6])]) 



        each=imudata[list(imudata.keys())[-1]]
        return each
        
    def __len__(self):
        return len(self.indexlist)
    def __getitem__(self, index):
        return self._get_item(index)

    def _get_item(self, index):        
        finalsource=self.indexlist[index]   #self.indexlist[np.random.choice(np.arange(0,self.length))]
        rgbpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'color')
        dpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'d2rgb')
        imupath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'data.txt')
        pointpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'pointcloud','points')
        colorpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'pointcloud','color')

        #geometrypath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'geometry')
        transfomationsourcepath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'transformation','odometry')
        
        rangenum=int(finalsource[3])-int(finalsource[2])
        
        pointcloud=np.zeros((self.maxclip,self.num,6))
        newpointpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'pointcloud')
        geometry=np.zeros((self.maxclip,18))  #transformation 12 6
        
        color_images=np.zeros((self.maxclip,3,2160,3840))  #transformation 12 6
        depth_images=np.zeros((self.maxclip,1,2160,3840)) 
        
        gt_xyz=np.zeros((self.maxclip,3)) 

        first=np.array([float(finalsource[4][0]),float(finalsource[4][1]),float(finalsource[4][2])])
        odometrylist=[]
        
        for idx in range(rangenum):
            # colorpath=os.path.join(rgbpath,str(idx+1+int(finalsource[2]))+'.jpg')
            # depathpath=os.path.join(dpath,str(idx+1+int(finalsource[2]))+'.png')
             
            # color_raw = o3d.io.read_image(colorpath)
            # depth_raw = o3d.io.read_image(depathpath)
            
            # rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
            #     color_raw, depth_raw)
            
            # inter = o3d.camera.PinholeCameraIntrinsic()
            # inter.set_intrinsics(3840, 2160, 1.80820276e+03, 1.80794556e+03, 1.94228662e+03, 1.12382178e+03)
            
            # pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, inter)





            # pcdpoint=np.load(os.path.join(pointpath,str(idx+1+int(finalsource[2]))+'.npy'))
            # pcdcolor=np.load(os.path.join(colorpath,str(idx+1+int(finalsource[2]))+'.npy'))

            # randomlist=np.random.choice(np.asarray(pcdpoint).shape[0],size=(self.num))
            
            # #pointcloud[idx,:,:]=farthest_point_sample(np.concatenate((pcdpoint,pcdcolor),1),8192)

            # pointcloud[idx,:,:3]=pcdpoint[randomlist]
            # pointcloud[idx,:,3:]=pcdcolor[randomlist]
            
            



            point=o3d.io.read_point_cloud(os.path.join(newpointpath,str(idx+1+int(finalsource[2]))+'.ply'))
            pointxyz=np.asarray(point.points)
            pointcolor=np.asarray(point.colors)

            randomlist=np.random.choice(pointxyz.shape[0],size=(self.num))
            pointcloud[idx,:,:3]=pointxyz[randomlist]
            pointcloud[idx,:,3:]=pointcolor[randomlist]
 
            odometrylist.append(np.load(os.path.join(transfomationsourcepath,str(idx+int(finalsource[2]))+'.npy')))
            odometry=reduce(np.dot, odometrylist)
            if idx ==0:
                gt_xyz[idx,:]=first
            else:
                gt_xyz[idx,:]=np.dot(np.linalg.inv(odometry),np.array([first[0], first[1], first[2], 1]))[:3]




            transfomationsource=np.load(os.path.join(transfomationsourcepath,str(idx+int(finalsource[2]))+'.npy'))[:3].reshape(-1)
            imudata=self.getimudata(imupath,1+idx+int(finalsource[2])).reshape(-1)
            #eachgeometry=np.load(os.path.join(geometrypath,str(idx+int(finalsource[2]))+'.npy')).reshape(-1)
            
            geometry[idx]=np.concatenate((transfomationsource,imudata),0) #np.concatenate((eachgeometry,transfomationsource),0)

            #color_images[idx] = np.asarray(color_raw).transpose(2,0,1)
            #depth_images[idx][0] = np.asarray(depth_raw)


        return gt_xyz,pointcloud,geometry,rangenum,finalsource#,color_images,depth_images


    # def _get_item(self, index):
         
    #     finalsource=self.indexlist[index]
    #     rgbpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'color')
    #     dpath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'d2rgb')
    #     #geometrypath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'geometry')
    #     transfomationsourcepath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'transformation','odometry')
    #     imupath=os.path.join(self.scenepath,finalsource[0],finalsource[1],'data.txt')
    #     rangenum=int(finalsource[3])-int(finalsource[2])
        
    #     pointcloud=np.zeros((self.maxclip,self.num,6))
        
    #     geometry=np.zeros((self.maxclip,12))  #transformation 12 6
        
    #     color_images=np.zeros((self.maxclip,3,2160,3840))  #transformation 12 6
    #     depth_images=np.zeros((self.maxclip,1,2160,3840)) 
        

        
    #     for idx in range(rangenum):
    #         colorpath=os.path.join(rgbpath,str(idx+1+int(finalsource[2]))+'.jpg')
    #         depathpath=os.path.join(dpath,str(idx+1+int(finalsource[2]))+'.png')
             
    #         color_raw = o3d.io.read_image(colorpath)
    #         depth_raw = o3d.io.read_image(depathpath)
            
    #         rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
    #             color_raw, depth_raw)
            
    #         inter = o3d.camera.PinholeCameraIntrinsic()
    #         inter.set_intrinsics(3840, 2160, 1.80820276e+03, 1.80794556e+03, 1.94228662e+03, 1.12382178e+03)
            
    #         pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, inter)
            
            
    #         randomlist=np.random.choice(np.asarray(pcd.colors).shape[0],size=(self.num))

            
    #         pointcloud[idx,:,:3]=np.asarray(pcd.points)[randomlist]
    #         pointcloud[idx,:,3:]=np.asarray(pcd.colors)[randomlist]

    #         transfomationsource=np.load(os.path.join(transfomationsourcepath,str(idx+int(finalsource[2]))+'.npy'))[:3].reshape(-1)
    #         imudata=self.getimudata(imupath,1+idx+int(finalsource[2])).reshape(-1)
    #         #eachgeometry=np.load(os.path.join(geometrypath,str(idx+int(finalsource[2]))+'.npy')).reshape(-1)
            
    #         geometry[idx]=np.concatenate((transfomationsource,imudata),0) #np.concatenate((eachgeometry,transfomationsource),0)

    #         #color_images[idx] = np.asarray(color_raw).transpose(2,0,1)
    #         #depth_images[idx][0] = np.asarray(depth_raw)
            

    #     gt_xyz=np.array([float(finalsource[4][0]),float(finalsource[4][1]),float(finalsource[4][2])])
        
    #     return gt_xyz,pointcloud,geometry,rangenum,finalsource,index#,color_images,depth_images

