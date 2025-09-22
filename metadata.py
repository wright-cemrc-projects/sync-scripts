#!/usr/bin/python3

import json
import datetime
import os

'''
Class wrapper for JSON metadata for a project
author: Matt Larson
date: 9-3-2020
'''

def getRelativeUNIX(windowsBasePath, windowsPath):
    ''' Convert windowsPath into a UNIX path relative to windowsBasePath '''
    if not windowsPath:
        return ''
    prefix = os.path.commonprefix([windowsBasePath + '\\', windowsPath])
    if not prefix:
        return windowsPath

    ## Split by the common prefix, if fails return full path.
    post = windowsPath.split(prefix, 1)
    if (len(post) > 1) :
        post = post[1]
        return post.replace('\\', '/')
    else : 
        return post[0]

# Required metadata
class DatasetMetadata:
    ''' Define the minimum required parameters '''
    startTime = datetime.datetime(2020, 7, 1, 18, 0)
    notes = ""
    pixel_size = 1.0
    voltage = 300
    spherical_aberration = 2.7
    amplitude_contrast = 0.1
    image_directories = ["/"]
    metadata_path = ""
    User = ""
    Group = ""
    instrument = ""
    camera = ""
    TypeOfSoftware = ""
    TiltRange = -1
    Workflow = "On"
    RelionMTF = None
    
    # These values can be defined by the calling script.
    FlipGain = None
    RotGain = None
    Throw = None

    def __init__(self, pathToJson):
        with open(pathToJson) as json_file:
            json_data = json.load(json_file)
        self.date = json_data['Date']
        self.description = json_data['SampleDescription']
        self.pixel_size = json_data['PixelSize']
        self.voltage = json_data['Voltage']
        self.spherical_aberration = json_data['SphericalAberration']
        self.amplitude_contrast = json_data['AmplitudeContrast']
        self.metadata_path = os.path.abspath(pathToJson)
        self.TypeOfSoftware = json_data["TypeOfSoftware"]
        self.User = json_data['User']
        self.Group = json_data['Group']
        self.DiscardFirstFrames = 0
        self.EvaluationDirectory = 'Evaluation'

        # add aretomo options
        self.AreTomo_AlignZ = None
        self.AreTomo_VolZ = None
        self.AreTomo_Patch = None
        self.AreTomo_TiltCor = None

        # metadata to know what system and detector were used
        if 'Instrument' in json_data:
            self.instrument = json_data['Instrument']
        if 'TypeOfCamera' in json_data:
            self.camera = json_data['TypeOfCamera']

        if 'UsingCDS' in json_data and json_data['UsingCDS'] == 'Yes':
            self.using_cds = True
        else:
            self.using_cds = False

        if 'LocationProject' in json_data:
            self.LocationProject = json_data['LocationProject']
        else:
            self.LocationProject = ''

        if 'TypeOfSoftware' in json_data:
            self.TypeOfSoftware = json_data['TypeOfSoftware']

        if 'TiltDirectory' in json_data:
            self.TiltDirectory = getRelativeUNIX(self.LocationProject, json_data['TiltDirectory'])

        if 'TiltRange' in json_data:
            self.TiltRange = json_data['TiltRange']

        if 'WorkflowOptions' in json_data:
            self.WorkflowOptions = json_data['WorkflowOptions']

        if 'TypeOfSession' in json_data:
            self.TypeOfSession = json_data['TypeOfSession']
        else:
            self.TypeOfSession = None

        if 'RelionMTF' in json_data:
            self.RelionMTF = json_data['RelionMTF']
        else:
            self.RelionMTF = self.buildMTFString(json_data)

        if 'DiscardFirstFrames' in json_data:
            self.DiscardFirstFrames = json_data['DiscardFirstFrames']

        # Check for AreTomo options
        if 'AreTomo_AlignZ' in json_data:
            self.AreTomo_AlignZ = json_data['AreTomo_AlignZ']

        if 'AreTomo_VolZ' in json_data:
            self.AreTomo_VolZ = json_data['AreTomo_VolZ']

        if 'AreTomo_TiltCor' in json_data:
            self.AreTomo_TiltCor = json_data['AreTomo_TiltCor']
        
        if 'AreTomo_Patch' in json_data:
            self.AreTomo_Patch = json_data['AreTomo_Patch']

    def buildMTFString(self, json_data):
        ''' Assemble from settings '''
        RelionMTF = ''
        try:
            if 'TypeOfCamera' in json_data:
                ''' f3-counting-200keV-mtf.star '''
                ''' k3-CDS-200keV-mtf.star '''

                if json_data['TypeOfCamera'] == 'Falcon 3EC':
                    RelionMTF = 'f3-'
                    if 'ModeOfCamera' in json_data and json_data['ModeOfCamera'] == 'Counting':
                        RelionMTF += 'counting-'
                    if 'ModeOfCamera' in json_data and json_data['ModeOfCamera'] == 'Linear':
                        RelionMTF += 'linear-'
                elif json_data['TypeOfCamera'] == 'Gatan K3':
                    RelionMTF = 'k3-'
                    if 'UsingCDS' in json_data and json_data['UsingCDS'] == 'Yes':
                        RelionMTF += 'CDS-'
                else: 
                    ''' Unknown type - no value '''
                    return None

                if 'Voltage' in json_data:
                    RelionMTF+=str(json_data['Voltage'])
                    RelionMTF+='keV-'

                RelionMTF+='mtf.star'

        except Exception as e:
            print(e)
        return RelionMTF

    def debugprint(self):
        print("Dataset description:")
        print(self.startTime)
        print(self.notes)
        print(self.pixel_size)
        print(self.voltage)
        print(self.spherical_aberration)
        print(self.amplitude_contrast)
