from PySide.QtCore import QObject,Slot,Signal
from SubDomain import *
from BFModule import *
from QueryEngine import *
from Query import * 

#
# The core boxfish engine connecting the different widgets
#
class BFEngine(QObject):

    # Name template for the highlight signal
    highlightSignal = "%s_highlight_signal"

    # Name template for the data publishing signal
    publishSignal = "%s_publish_signal"
    
    # The list of registered signals for highlights and yes the exec stuff is
    # necessary since PySide seems to mangle the signal otherwise. It is not
    # allowed to create the signals in the __init__ function nor can we create a
    # list of signale or a dict(). Either code runs but the resulting signals
    # are castrated (they have no connect function for example). Thus we use
    # this hack to create a bunch of named static variables
    for name in SubDomain().subclasses():
        exec highlightSignal % name + ' = Signal(SubDomain)'
        exec publishSignal % name + ' = Signal(Query,np.ndarray)'

    # The signal to indicate that the globally available attributes have changed
    attributesChanged = Signal(dict)

    
    def __init__(self):
        QObject.__init__(self)

        # PySide is doing some behind the scene magic to take the static
        # variables we created above and turn them intolocal variables of the
        # same name. For convinience we now create a map to access them by their
        # name. The map stores the signal as well as the corresponding count
        self.listenerCount = dict()
        self.highlights = dict()
        self.publish = dict()
        for name in SubDomain().subclasses():
            self.listenerCount[name] = 0
            exec 'self.highlights[\"%s\"] = self.' % name + self.highlightSignal % name 
            exec 'self.publish[\"%s\"] = self.' % name + self.publishSignal % name

        self.context = Context()
        self.queryEngine = QueryEngine()
        
        
    def registerModule(self,module):
        
        module.subscribeSignal.connect(self.subscribe)
        module.unsubscribeSignal.connect(self.unsubscribe)
        module.highlightSignal.connect(self.highlight)
        module.registerTableSignal.connect(self.registerTable)
        module.registerProjectionSignal.connect(self.registerProjection)
        module.evaluateSignal.connect(self.evaluate)
        module.getSubDomainSignal.connect(self.getSubDomain)

        self.attributesChanged.connect(module.attributesChanged)
    
    @Slot(SubDomain)
    def highlight(self,subdomain):
        """This slot is called whenever a module changed a highlight. The engine
           will cycle through all subscribed listeners and try to map the set of
           highlighted elements to the corresponding set elements in the target
           domain. For all type for which the context provides such a projection
           the engine will emit a highlight signal.
        """

        # For all possible listeners
        for key in self.listenerCount:

            # If somebody issubscribed to this somain
            if self.listenerCount[key] > 0:

                # If this somebody is listening for exactly this signal
                if key == subdomain.subdomain():
                    self.highlights[key].emit(subdomain) # We pass the message on
                # Otherwise, if our context can project the highlight into the
                # correct subdomain
                elif self.context.relates(subdomain,key):
                    self.highlights[key].emit(self.context.project(subdomain,key))
                    


    @Slot(BFModule,str)
    def subscribe(self,module,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s. Must be a subclass of SubDomain" % name)

        self.listenerCount[name] = self.listenerCount[name] + 1

        self.connectSubscription(module,name)
             
    
    @Slot(BFModule,str)
    def unsubscribe(self,module,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s. Must be a subclass of SubDomain" % name)

        if self.listenerCount[name] == 0:
            raise ValueError("No listener left to unsubscribe")

        self.listenerCount[name] = self.listenerCount[name] - 1

        self.disconnectSubscription(module,name)

    @Slot(BFTable)
    def registerTable(self,table):
        print "BFEngine: registerTable"
        
        self.queryEngine.addTable(table)

        self.attributesChanged.emit(self.queryEngine.attributes)
      
    @Slot(Projection)
    def registerProjection(self,projection):

        self.context.addProjection(projection)

    @Slot(Query)
    def evaluate(self,query):

        answer, success = self.queryEngine.evaluate(query,self.context)
        if success:
            self.publish[query.subdomain.subdomain()].emit(query,answer)

    @Slot(BFModule,str)
    def getSubDomain(self,module,subdomain):

        data,success = self.queryEngine.getSubDomain(subdomain)
        if success:
            module.setSubDomain(data)
    
    def connectSubscription(self,module,name):

        self.highlights[name].connect(module.highlightChanged)
        self.publish[name].connect(module.receive)


    def disconnectSubscription(self,module,name):

        self.highlights[name].disconnect(module.highlightChanged)
        self.publish[name].disconnect(module.receive)

        
        
if __name__ == '__main__':

  from PySide.QtGui import QApplication
  from BFTable import *
  from Context import *
  from Query import *
  from Projection import *
  import sys

  # Create a basic app to handle the signals
  app = QApplication(sys.argv)
  
  # Create the center engine
  hub = BFEngine()
  
  m0 = BFModule()
  m1 = BFModule()
  
  hub.registerModule(m0)
  hub.registerModule(m1)
  
  m0.subscribe(Ranks().subdomain())
  m0.subscribe(Cores().subdomain())
  m0.subscribe(Nodes().subdomain())
  
  m1.subscribe(Nodes().subdomain())
  m1.subscribe(Ranks().subdomain())
  
  m0.highlightSignal.emit(Cores())
  m0.highlightSignal.emit(Nodes())
  
  
  m0.unsubscribe(Nodes().subdomain())
  
  m0.highlightSignal.emit(Nodes())
  
  table = BFTable()
  table.fromYAML(Ranks,'mpirank','bgpcounter_data.yaml')

  m0.addTable(table)

  # For testing purposes load the same file but us tx as core id
  table2 = BFTable()
  table2.fromYAML(Cores,'tx','bgpcounter_data.yaml')

  m1.addTable(table2)

  # Setup a simple query

  # For "cores" 0,1, and 2
  c = Cores((0,1,2))

  # Compute the average ty value 
  q = Query(c,'ty','mean')

  # Note that only m0 is subscribed to cores
  m0.evaluate(q)

  # Now setup a query that requires mapping. Since the tx value is used as the
  # primary key it is actually only available in the Ranks table
  q = Query(c,'tx','mean')

  # This query will fail since we have not defined a mapping yet
  m1.evaluate(q)

  # Define the identity map between cores and ranks
  p = Identity(Cores(),Ranks())

  m0.addProjection(p)

  # Try the query again. Note that we added the projection to m0 but still the
  # m1 query can use it
  m1.evaluate(q)
  
  
