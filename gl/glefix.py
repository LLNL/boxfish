"""This handles the absence of gleSetNumSlices and gleGetNumSlices on macs that
   use an older version of OpenGL.
"""
from ctypes import c_int
from OpenGL import platform
from OpenGL.GLE import gleGetNumSides, gleSetNumSides

if not bool(gleGetNumSides):
    # If no getnumsides, try mapping to the older gleGetNumSlices
    gleGetNumSides = platform.createBaseFunction(
        'gleGetNumSlices', dll=platform.GLE, resultType=c_int,
        argTypes=[],
        doc='gleGetNumSlices(  ) -> c_int',
        argNames=())

    gleSetNumSides = platform.createBaseFunction(
        'gleSetNumSlices', dll=platform.GLE, resultType=None,
        argTypes=[c_int],
        doc='gleSetNumSlices( c_int(slices) ) -> None',
        argNames=('slices',))

    try:
        gleGetNumSides()
    except:
        # Set to no-ops if nothing actually ends up working.
        gleGetNumSides = int
        gleSetNumSides = int

