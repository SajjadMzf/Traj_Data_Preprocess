import numpy as np
import pandas as pd
import  os
import pickle
import matplotlib.pyplot as plt

import params as p
from data_frame_functions import group_df, group2df
import coordinate_functions as cf
from utils_functions import digital_filter
# From ID,Frame,X,Y to xVelocity, yVelocity, xAcceleration, yAcceleration, SVs_ID
class PreprocessData():
    def __init__(self, data_files, lane_markings_file):
        self.lane_markings = pd.read_csv(lane_markings_file)
        self.lane_markings = self.lane_markings.to_dict(orient='list')
        self.lane_markings_xy, self.lane_markings_ds = self.get_lane_markings()
        self.lane_markings_s = np.mean(self.lane_markings_ds[:,:,1], axis=0)
        
        self.data_files = data_files

        self.data_df_list = []
        self.track_data_list = []
        self.frame_data_list = []
        for data_file in data_files:
            df = pd.read_csv(data_file)
            self.data_df_list.append(df)
        
        self.metas_columns = ['id','frameRate','locationId','speedLimit','month','weekDay','startTime',
                            'duration','totalDrivenDistance','totalDrivenTime','numVehicles','numCars','numTrucks','upperLaneMarkings','lowerLaneMarkings']
        self.statics_columns = ['id','width','height','initialFrame','finalFrame','numFrames','class',
                            'drivingDirection','traveledDistance','minXVelocity','maxXVelocity','meanXVelocity','minDHW','minTHW','minTTC','numLaneChanges']

    def export_statics_metas(self):
        meta_data = [-1]*len(self.metas_columns)
        meta_data[self.metas_columns.index('upperLaneMarkings')] = self.lane_markings_s.tolist()
        print(meta_data)
        print(self.metas_columns)
        meta_df = pd.DataFrame([meta_data], columns= self.metas_columns)
        for df_itr, df in enumerate(self.data_df_list):
            

            static_df = pd.DataFrame()
            static_df[p.TRACK_ID] = df[p.TRACK_ID]
            remaining_columns = self.statics_columns
            static_df['drivingDirection'] = np.ones((len(static_df[p.TRACK_ID]))) 
            remaining_columns.remove('id')
            remaining_columns.remove('drivingDirection')
            
            for column in remaining_columns:
                static_df[column] = np.ones((len(static_df[p.TRACK_ID])))*-1
            
            meta_data_file = self.data_files[df_itr].split('.csv')[0] + '_recordingMeta.csv'
            static_data_file = self.data_files[df_itr].split('.csv')[0] + '_tracksMeta.csv'
            
            meta_df.to_csv(meta_data_file, index = False)
            static_df.to_csv(static_data_file, index = False)
            

    def export_df(self, name_extension,column_list):
        for file_itr, data_file in enumerate(self.data_files):
            pr_data_file = data_file.split('.csv')[0] + name_extension + '.csv'
            df = self.data_df_list[file_itr][column_list]
            df.sort_values(by=[p.ID, p.FRAME], inplace = True)
            df.to_csv(pr_data_file, index = False)

    def update_track_frame_data_list(self):
        self.track_data_list = []
        self.frame_data_list = []
        for df_itr in range(len(self.data_df_list)):
            self.track_data_list.append(group_df(self.data_df_list[df_itr],by = p.TRACK_ID))
            self.frame_data_list.append(group_df(self.data_df_list[df_itr], by = p.FRAME))

    def update_df(self, source = 'track_data'):
        if source == 'track_data':
            self.data_df_list = []  
            self.frame_data_list = []
            for track_data in self.track_data_list:
                df = group2df(track_data)
                self.data_df_list.append(df)      
                self.frame_data_list.append(group_df(df, by = p.FRAME))
        elif source == 'frame_data':
            self.data_df_list = []  
            self.track_data_list = []
            for frame_data in self.frame_data_list:
                df = group2df(frame_data)
                self.data_df_list.append(df)      
                self.track_data_list.append(group_df(df, by = p.TRACK_ID))
        else:
            raise(ValueError('Unknown Source'))
    
    def initial_cleaning(self):
        for df_itr, df in enumerate(self.data_df_list):
            
            # Select required columns and disregard the rest
            df.drop(columns=df.columns.difference([p.FRAME, p.ID, p.X, p.Y]), inplace=True)
            
            # convert to image coordinate
            df[p.Y] = df[p.Y].apply(lambda x: x*-1)

            # drop samples with x or y larger than max allowed x,y or smaller than min 
            min_lane_x = np.amin(self.lane_markings_xy[:,:,0])
            min_lane_y = np.amin(self.lane_markings_xy[:,:,1])
            
            max_lane_x = np.amax(self.lane_markings_xy[:,:,0])
            max_lane_y = np.amax(self.lane_markings_xy[:,:,1])
            df.drop(df[df[p.X]>max_lane_x].index, inplace=True)
            df.drop(df[df[p.Y]>max_lane_y].index, inplace=True)
            df.drop(df[df[p.X]<min_lane_x].index, inplace=True)
            df.drop(df[df[p.Y]<min_lane_y].index, inplace=True)
            
            # Adding vehicle length and width columns
            df[p.WIDTH] = p.AVG_LENGTH * np.ones((len(df)))
            df[p.HEIGHT] = p.AVG_WIDTH * np.ones((len(df)))
            self.data_df_list[df_itr] = df

            # Initialising new columns:
            df[p.X_VELOCITY] = np.zeros((len(df)))
            df[p.Y_VELOCITY] = np.zeros((len(df)))
            df[p.X_ACCELERATION] = np.zeros((len(df)))
            df[p.Y_ACCELERATION] = np.zeros((len(df)))
            
            df[p.PRECEDING_ID] = np.zeros((len(df)))
            df[p.RIGHT_PRECEDING_ID] = np.zeros((len(df)))
            df[p.LEFT_PRECEDING_ID] = np.zeros((len(df)))

            df[p.FOLLOWING_ID] = np.zeros((len(df)))
            df[p.RIGHT_FOLLOWING_ID] = np.zeros((len(df)))
            df[p.LEFT_FOLLOWING_ID] = np.zeros((len(df)))

            df[p.RIGHT_ALONGSIDE_ID] = np.zeros((len(df)))
            df[p.LEFT_ALONGSIDE_ID] = np.zeros((len(df)))

            df[p.D_S] = np.zeros((len(df)))
            df[p.S_S] = np.zeros((len(df)))
        
        
    def convert2frenet(self, frenet_ref):
        for file_itr in range(len(self.track_data_list)):
            # convert to frenet frame
            for id, track_data in enumerate(self.track_data_list[file_itr]):
                num_frames = len(track_data[p.X])
                traj = np.zeros((num_frames,2))
                traj[:,0] = track_data[p.X]
                traj[:,1] = track_data[p.Y]
                traj_frenet, _ = cf.cart2frenet(traj,frenet_ref)
                self.track_data_list[file_itr][id][p.D] = traj_frenet[:,0]
                self.track_data_list[file_itr][id][p.S] = traj_frenet[:,1]

    
    def get_lane_id(self):
        for file_itr in range(len(self.track_data_list)):
            olv_c = 0
            ilv_c = 0
            for id, track_data in enumerate(self.track_data_list[file_itr]):
                total_frames = len(track_data[p.X])
                lane_id = np.zeros((total_frames))
                for fr in range(total_frames):
                    for i in range(3):
                        if track_data[p.S][fr]<=self.lane_markings_s[i+1] and track_data[p.S][fr]>=self.lane_markings_s[i]:
                            lane_id[fr] = i+1
                    if track_data[p.S][fr]<self.lane_markings_s[0]:
                        ilv_c +=1
                    
                    if track_data[p.S][fr]>self.lane_markings_s[3]:
                        olv_c +=1
                        lane_id[fr] = 3
                    
                self.track_data_list[file_itr][id][p.LANE_ID] = lane_id
            print('File: {}. Outer lane violation counts (classified as lane 3): {}, Inner lane violation counts (classified as lane 0): {}'.format(file_itr+1, olv_c, ilv_c))      
    
    def estimate_vel_acc(self):
        # https://en.wikipedia.org/wiki/Savitzky%E2%80%93Golay_filter
        # velo -2,-1,0,1,2/10
        # acc 2,-1,-2,-1,2/7
        for file_itr in range(len(self.track_data_list)):
            for id, track_data in enumerate(self.track_data_list[file_itr]):
                x = track_data[p.D]
                y = track_data[p.S]
                x_smooth = digital_filter(x, [-21,14,39,54,59,54,39,14,-21],231, smoothing = True)
                y_smooth = digital_filter(y, [-21,14,39,54,59,54,39,14,-21],231, smoothing = True)
                x_velo = digital_filter(x_smooth, np.array([-2,-1,0,1,2]), 10)
                y_velo = digital_filter(y_smooth, np.array([-2,-1,0,1,2]), 10)
                x_acc = digital_filter(x_velo, np.array([-2,-1,0,1,2]), 10)
                y_acc = digital_filter(y_velo, np.array([-2,-1,0,1,2]), 10)
                self.track_data_list[file_itr][id][p.D_S] = x_smooth
                self.track_data_list[file_itr][id][p.S_S] = y_smooth
                
                self.track_data_list[file_itr][id][p.X_VELOCITY] = x_velo
                self.track_data_list[file_itr][id][p.Y_VELOCITY] = y_velo

                self.track_data_list[file_itr][id][p.X_ACCELERATION] = x_acc
                self.track_data_list[file_itr][id][p.Y_ACCELERATION] = y_acc    
        
    
            
    def calculate_svs(self):
        for file_itr in range(len(self.frame_data_list)):
            for frame_itr, frame_data in enumerate(self.frame_data_list[file_itr]):
                for track_itr, track_id in enumerate(frame_data[p.ID]):
                    lane_id = frame_data[p.LANE_ID][frame_data[p.ID] == track_id]
                    vehicle_front_xloc = frame_data[p.D][frame_data[p.ID] == track_id] + frame_data[p.WIDTH][frame_data[p.ID] == track_id]/2
                    vehicle_back_xloc = frame_data[p.D][frame_data[p.ID] == track_id] - frame_data[p.WIDTH][frame_data[p.ID] == track_id]/2
                    same_lane_vehicles_itrs = frame_data[p.LANE_ID] == lane_id
                    right_lane_vehicles_itrs = frame_data[p.LANE_ID] == lane_id+1
                    left_lane_vehicles_itrs = frame_data[p.LANE_ID] == lane_id-1

                    preceding_vehicles_itrs = (frame_data[p.D] - frame_data[p.WIDTH]/2)> vehicle_front_xloc
                    following_vehicles_itrs = (frame_data[p.D] + frame_data[p.WIDTH]/2)< vehicle_back_xloc
                    alongside_vehicles_itrs = np.logical_not(np.logical_or(preceding_vehicles_itrs, following_vehicles_itrs))

                    rpv_itrs = np.nonzero(np.logical_and(preceding_vehicles_itrs, right_lane_vehicles_itrs))[0]
                    lpv_itrs = np.nonzero(np.logical_and(preceding_vehicles_itrs, left_lane_vehicles_itrs))[0]
                    pv_itrs = np.nonzero(np.logical_and(preceding_vehicles_itrs, same_lane_vehicles_itrs))[0]

                    rfv_itrs = np.nonzero(np.logical_and(following_vehicles_itrs, right_lane_vehicles_itrs))[0]
                    lfv_itrs = np.nonzero(np.logical_and(following_vehicles_itrs, left_lane_vehicles_itrs))[0]
                    fv_itrs = np.nonzero(np.logical_and(following_vehicles_itrs, same_lane_vehicles_itrs))[0]

                    rav_itrs = np.nonzero(np.logical_and(alongside_vehicles_itrs, right_lane_vehicles_itrs))[0]
                    lav_itrs = np.nonzero(np.logical_and(alongside_vehicles_itrs, left_lane_vehicles_itrs))[0]

                    if len(rav_itrs)>0:
                        rav_itr = np.argmin(abs(frame_data[p.D][rav_itrs] + frame_data[p.WIDTH][rav_itrs]/2 - vehicle_back_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.RIGHT_ALONGSIDE_ID][track_itr] = frame_data[p.ID][rav_itrs[rav_itr]]                                            

                    if len(lav_itrs)>0:
                        lav_itr = np.argmin(abs(frame_data[p.D][lav_itrs] + frame_data[p.WIDTH][lav_itrs]/2 - vehicle_back_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.LEFT_ALONGSIDE_ID][track_itr] = frame_data[p.ID][lav_itrs[lav_itr]]      
                    
                    if len(rpv_itrs)>0:
                        rpv_itr = np.argmin(abs(frame_data[p.D][rpv_itrs]- vehicle_front_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.RIGHT_PRECEDING_ID][track_itr] = frame_data[p.ID][rpv_itrs[rpv_itr]]
                    if len(lpv_itrs)>0:
                        lpv_itr = np.argmin(abs(frame_data[p.D][lpv_itrs]- vehicle_front_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.LEFT_PRECEDING_ID][track_itr] = frame_data[p.ID][lpv_itrs[lpv_itr]]
                    if len(pv_itrs)>0:
                        pv_itr = np.argmin(abs(frame_data[p.D][pv_itrs]- vehicle_front_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.PRECEDING_ID][track_itr] = frame_data[p.ID][pv_itrs[pv_itr]]

                    if len(fv_itrs)>0:
                        fv_itr = np.argmin(abs(frame_data[p.D][fv_itrs]- vehicle_back_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.FOLLOWING_ID][track_itr] = frame_data[p.ID][fv_itrs[fv_itr]]
                    
                    if len(rfv_itrs)>0:
                        rfv_itr = np.argmin(abs(frame_data[p.D][rfv_itrs]- vehicle_back_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.RIGHT_FOLLOWING_ID][track_itr] = frame_data[p.ID][rfv_itrs[rfv_itr]]
                    
                    if len(lfv_itrs)>0:
                        lfv_itr = np.argmin(abs(frame_data[p.D][lfv_itrs]- vehicle_back_xloc))
                        self.frame_data_list[file_itr][frame_itr][p.LEFT_FOLLOWING_ID][track_itr] = frame_data[p.ID][lfv_itrs[lfv_itr]]             
    
    def get_lane_markings(self):
        lane_marking_length = len(np.array(self.lane_markings[p.lon_1]))
        lane_markings_xy = np.zeros((lane_marking_length,4,2))

        lon1 = np.array(self.lane_markings[p.lon_1]) #+ p.X_BIAS
        lat1 = np.array(self.lane_markings[p.lat_1]) #+ p.Y_BIAS
        lon2 = np.array(self.lane_markings[p.lon_2]) #+ p.X_BIAS
        lat2 = np.array(self.lane_markings[p.lat_2]) #+ p.Y_BIAS
        lon3 = np.array(self.lane_markings[p.lon_3]) #+ p.X_BIAS
        lat3 = np.array(self.lane_markings[p.lat_3]) #+ p.Y_BIAS

        (x1, y1) = cf.longlat2xy((lon1, lat1), (p.ORIGIN_LON, p.ORIGIN_LAT))
        (x2, y2) = cf.longlat2xy((lon2, lat2), (p.ORIGIN_LON, p.ORIGIN_LAT))
        (x3, y3) = cf.longlat2xy((lon3, lat3), (p.ORIGIN_LON, p.ORIGIN_LAT))
        
        y1 *= -1
        y2 *= -1
        y3 *= -1

        lane_markings_xy[:,1,0] = x1 + (x2-x1)/2
        lane_markings_xy[:,1,1] = y1 + (y2-y1)/2
        lane_markings_xy[:,2,0] = x2 + (x3-x2)/2
        lane_markings_xy[:,2,1] = y2 + (y3-y2)/2
        
        lane_markings_xy[:,0,0] = x1 - (x2-x1)/2
        lane_markings_xy[:,0,1] = y1 - (y2-y1)/2
        lane_markings_xy[:,3,0] = x3 + (x3-x2)/2
        lane_markings_xy[:,3,1] = y3 + (y3-y2)/2

        lane_markings_ds = np.zeros_like(lane_markings_xy)

        for i in range(lane_markings_xy.shape[1]):
            if i == 0:
                continue
            lane_markings_ds[:,i], ref_frenet = cf.cart2frenet(lane_markings_xy[:,i],lane_markings_xy[:,0])
        lane_markings_ds[:,0] = ref_frenet

        return lane_markings_xy, lane_markings_ds
      
    


if __name__ == '__main__':
    
    '''
    column_list = [p.FRAME, p.TRACK_ID, p.X, p.Y, p.S, p.D, p.S_S, p.D_S, p.WIDTH, p.HEIGHT, 
                p.X_VELOCITY, p.Y_VELOCITY, p.X_ACCELERATION, p.Y_ACCELERATION,
                p.PRECEDING_ID, p.FOLLOWING_ID, p.LEFT_PRECEDING_ID, p.LEFT_ALONGSIDE_ID, p.LEFT_FOLLOWING_ID,
                p.RIGHT_PRECEDING_ID, p.RIGHT_ALONGSIDE_ID, p.RIGHT_FOLLOWING_ID, p.LANE_ID ]
    preprocess = PreprocessData(p.DATA_FILES, p.LANE_MARKINGS_FILE)
    preprocess.initial_cleaning() # Clean df
    preprocess.update_track_frame_data_list() # group by track id and frame
    preprocess.convert2frenet(preprocess.lane_markings_xy[:,0]) #convert track groups to frenet coordinates
    preprocess.get_lane_id() # get lane ids for track groups
    preprocess.estimate_vel_acc() # estimate velocity and acceleration on each track group
    preprocess.update_df(source='track_data') # update df and frame groups based on track group
    preprocess.calculate_svs() # calculate SV ids on frame groups
    preprocess.update_df(source='frame_data') # update df and track groups based on frame group
    preprocess.export_df(name_extension='_processed', column_list = column_list)
    '''
    ## export statics meta:
    processed_data = ['./M40draft2_processed.csv']
    preprocess = PreprocessData(processed_data, p.LANE_MARKINGS_FILE)
    preprocess.export_statics_metas()