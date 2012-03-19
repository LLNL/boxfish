from PySide.QtCore import Slot,Signal
from PySide.QtGui import QFrame
import numpy as np
from SubDomain import *
from BFTable import *
from Query import *
from Projection import *

class BFModule(QFrame):

    subscribeSignal          = Signal(object,str)
    unsubscribeSignal        = Signal(object,str)
    highlightSignal          = Signal(SubDomain)
    registerTableSignal      = Signal(BFTable)
    registerProjectionSignal = Signal(Projection)
    evaluateSignal           = Signal(Query)
    getSubDomainSignal       = Signal(object,str)
    
    def __init__(self,parent=None):

        super(BFModule,self).__init__(parent)
        self.attributes = dict()

    def subscribe(self,name):
        self.subscribeSignal.emit(self,name)

    def unsubscribe(self,name):
        self.unsubscribeSignal.emit(self,name)

    def addTable(self,table):
        self.registerTableSignal.emit(table)

    def addProjection(self,projection):
        self.registerProjectionSignal.emit(projection)

    def evaluate(self,query):
        self.evaluateSignal.emit(query)

    def highlight(self,subdomain):
        self.highlightSignal.emit(subdomain)

    def getSubDomain(self,subdomain):
        self.getSubDomainSignal.emit(self,subdomain)

    def setSubDomain(self,subdomain):
        self.subdomain = subdomain
    
    @Slot(SubDomain)
    def highlightChanged(self,subdomain):
        print "Highlight", subdomain.subdomain()

    @Slot(Query,np.ndarray)
    def receive(self,query,data):
        print "BFModule got an answer for ", query 

    @Slot(dict)
    def attributesChanged(self,attributes):
        """Whenever the global list of available attributes changes this
           function is called
        """
        print "BFModule.updateAttributes ", attributes, "\n\n"
        self.attributes = attributes
    
        
