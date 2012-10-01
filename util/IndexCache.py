
class IndexFunctionCache(object):
    """This class implements a cache for functions that take
       multidimensional indices as parameters.  User needs
       only providet the function and call this instead.

       The function should take index tuples as parameters.
    """
    def __init__(self, function, shape):
        """Init the cache as a numpy array and store the function so
           that we can call it when we need to."""
        self.function = function
        self.cache = np.empty(shape, dtype=object)

    shape = property(lambda self: self.cache.shape)

    def __call__(self, node):
        """Get the cached value of a function, generating it if need be."""
        node = tuple(node)  # Ensure numpy it's an index, not a slice.
        if self.cache[node] == None:
            self.cache[node] = self.function(node)
        return self.cache[node]
