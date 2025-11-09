from __main__ import qt, ctk, vtk, slicer

import os
import logging

from .PedicleScrewSimulatorStep import *
from .Helper import *

class DummySpineStep(PedicleScrewSimulatorStep):

    def __init__( self, stepid ): 
      self.initialize( stepid )
      self.setName( '0. Dummy Spine Models' )
      self.setDescription( """Load pre-built dummy spine models separated by region: Cervical, Thoracic, Lumbar, Sacrococcygeal.""")

      self.__parent = super( DummySpineStep, self )

    def createUserInterface( self ): 
      self.__layout = self.__parent.createUserInterface()

      # Explanation
      info = qt.QLabel('Select a spine region to show/hide vertebrae. All models are loaded automatically from Resources/3DModels when this step is entered.')
      info.setWordWrap(True)
      self.__layout.addRow(info)

      # Spacer
      self.__layout.addRow(qt.QLabel(""))

      # Region selection buttons
      regionLabel = qt.QLabel('Toggle visibility for Spine Regions:')
      regionLabel.font.setBold(True)
      self.__layout.addRow(regionLabel)

      self.buttonBox = qt.QWidget()
      self.buttonLayout = qt.QVBoxLayout(self.buttonBox)
      self.buttonLayout.setAlignment(qt.Qt.AlignTop)

      self.btnCervical = qt.QPushButton('Cervical')
      self.btnThoracic = qt.QPushButton('Thoracic')
      self.btnLumbar = qt.QPushButton('Lumbar')
      self.btnSacrococcygeal = qt.QPushButton('Sacrococcygeal')

      for b in (self.btnCervical, self.btnThoracic, self.btnLumbar, self.btnSacrococcygeal):
        b.setMinimumHeight(50) # Enlarge buttons
        b.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        self.buttonLayout.addWidget(b)

      self.__layout.addRow(self.buttonBox)

      # Connect buttons to toggle region model visibility
      self.btnCervical.connect('clicked(bool)', lambda : self._toggleRegionModels('cervical'))
      self.btnThoracic.connect('clicked(bool)', lambda : self._toggleRegionModels('thoracic'))
      self.btnLumbar.connect('clicked(bool)', lambda : self._toggleRegionModels('lumbar'))
      self.btnSacrococcygeal.connect('clicked(bool)', lambda : self._toggleRegionModels('sacrococcygeal'))

      qt.QTimer.singleShot(0, self.killButton)

    def killButton(self):
      # hide useless button
      bl = slicer.util.findChildren(text='Final')
      if len(bl):
        bl[0].hide()

    def _loadAllSpineModels(self):
      """Load all model files found in the module Resources/3DModels folder.
      Loaded nodes are tagged with node.SetAttribute('PedicleScrewSimulator','1') and a 'region' attribute.
      """
      try:
        moduleDir = os.path.dirname(__file__)
        modelsDir = os.path.normpath(os.path.join(moduleDir, '..', 'Resources', '3DModels'))
        if not os.path.isdir(modelsDir):
          return
        # collect files
        files = []
        for fname in os.listdir(modelsDir):
          if fname.lower().endswith(('.obj', '.stl', '.ply', '.vtp')):
            files.append(os.path.join(modelsDir, fname))

        self._spineModels = []
        for p in files:
          try:
            loaded = slicer.util.loadModel(p, returnNode=True)
            if isinstance(loaded, tuple):
              modelNode = loaded[1]
            else:
              modelNode = loaded
            if not modelNode:
              continue
            name = os.path.basename(p).split('.')[0]
            modelNode.SetName(name)
            # tag node so we can find it later
            modelNode.SetAttribute('PedicleScrewSimulator', '1')
            # determine region by prefix
            up = name.upper()
            region = ''
            if up.startswith('C'):
              region = 'cervical'
            elif up.startswith('T'):
              region = 'thoracic'
            elif up.startswith('L'):
              region = 'lumbar'
            elif up.startswith('SC') or up.startswith('S'):
              region = 'sacrococcygeal'
            modelNode.SetAttribute('PedicleScrewSimulator.region', region)
            # ensure visible by default
            try:
              modelNode.GetDisplayNode().SetVisibility(True)
            except Exception:
              pass
            self._spineModels.append(modelNode.GetID())
          except Exception as e:
            logging.debug('Failed to load spine model %s: %s' % (p, str(e)))
      except Exception:
        pass
      
    def createOrSelectROI(self, region):
      """Create or select a vtkMRMLMarkupsROINode for the specified spine region."""
      roiNodeName = 'SpineROI_' + region.capitalize()
      roiNode = slicer.mrmlScene.GetFirstNodeByName(roiNodeName)

      if not roiNode:
        roiNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsROINode')
        roiNode.SetName(roiNodeName)
        roiNode.CreateDefaultDisplayNodes()
        roiNode.GetDisplayNode().SetFillVisibility(False)
        roiNode.GetDisplayNode().SetVisibility(True)

        # Set approximate default positions/radii for spine regions
        # These are rough estimates and might need fine-tuning
        if region == 'cervical':
          roiNode.SetRadiusXYZ(30, 30, 50)
          roiNode.SetXYZ(0, -30, 100) # Example: higher up
        elif region == 'thoracic':
          roiNode.SetRadiusXYZ(40, 40, 80)
          roiNode.SetXYZ(0, -40, 0) # Example: middle back
        elif region == 'lumbar':
          roiNode.SetRadiusXYZ(50, 50, 70)
          roiNode.SetXYZ(0, -50, -100) # Example: lower back
        elif region == 'sacrococcygeal':
          roiNode.SetRadiusXYZ(40, 40, 60)
          roiNode.SetXYZ(0, -40, -180) # Example: lowest part
        
        slicer.util.showStatusMessage('Created ROI for %s region.' % region.capitalize(), 3000)
      else:
        roiNode.GetDisplayNode().SetVisibility(True)
        slicer.util.showStatusMessage('Selected existing ROI for %s region.' % region.capitalize(), 3000)

      # Ensure 3D view is active and camera is focused on the ROI
      lm = slicer.app.layoutManager()
      lm.setLayout(3) # 3D only layout
      
      # Center 3D view on ROI
      viewNode = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLViewNode')
      if viewNode:
        bounds = [0]*6
        roiNode.GetRASBounds(bounds)
        center = [(bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2]
        viewNode.SetFocalPoint(center[0], center[1], center[2])
        # Adjust camera position to see the ROI
        viewNode.SetViewPosition(center[0], center[1] - 200, center[2]) # Move camera back
        viewNode.SetViewUp(0, 0, 1) # Standard view up
      # Store ROI in module parameter node so other steps (e.g. DefineROI) can pick it up
      try:
        pNode = self.parameterNode()
        if pNode:
          pNode.SetNodeReferenceID('roiNode', roiNode.GetID())
          pNode.SetParameter('roiRegion', region)
      except Exception:
        # non-fatal: parameter node might not be available in some contexts
        pass

    def _toggleRegionModels(self, region):
      """Toggle visibility for all loaded models in the given region."""
      # Find model nodes tagged by attribute or by name prefix
      models = []
      try:
        for n in slicer.mrmlScene.GetNodesByClass('vtkMRMLModelNode'):
          node = n
          if node.GetAttribute('PedicleScrewSimulator') == '1':
            r = node.GetAttribute('PedicleScrewSimulator.region')
            if r == region:
              models.append(node)
      except Exception:
        pass

      # Toggle: if at least one visible -> hide all, else show all
      anyVisible = False
      for m in models:
        try:
          if m.GetDisplayNode() and m.GetDisplayNode().GetVisibility():
            anyVisible = True
            break
        except Exception:
          continue

      for m in models:
        try:
          if m.GetDisplayNode():
            m.GetDisplayNode().SetVisibility(False if anyVisible else True)
        except Exception:
          continue

    # Minimal validate: always allow next
    def validate(self, desiredBranchId):
      self.__parent.validate(desiredBranchId)
      self.__parent.validationSucceeded(desiredBranchId)

    def onEntry(self, comingFrom, transitionType):
      """When entering this step, force 3D-only layout and auto-load all models from Resources/3DModels."""
      super(DummySpineStep, self).onEntry(comingFrom, transitionType)
      # Force 3D-only layout
      try:
        lm = slicer.app.layoutManager()
        lm.setLayout(3)
      except Exception:
        pass

      # Load all spine models packaged in Resources/3DModels
      try:
        self._loadAllSpineModels()
      except Exception as e:
        logging.debug('Error loading spine models: %s' % str(e))