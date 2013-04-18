Download and Install
====================

Download
--------
Boxfish is available on the `PAVE <https://scalability.llnl.gov/performance-analysis-through-visualization/software.php>`_ website

Install
--------

Boxfish requires a Python 2.7, Qt 4.7+, numpy 1.6+, matplotlib 1.1.0+, PySide
1.0.1+, PyYaml and PyOpenGL. Ubuntu users may also need to install libgle3. 

To build the documentation, you need `Sphinx <http://sphinx-doc.org>`_.

To run the Boxfish executable, the Boxfish install directory should be included in your PYTHONPATH environment variable.

Run
---

Boxfish recognizes meta files that can be input at Boxfish launch or
through the ``File`` menu of the Boxfish GUI. See :ref:`file-format-label`
for meta file requirements and :ref:`bfmodules` pages for any additional
requirements per module.

.. code-block:: none

  boxfish_install_directory> bin/boxfish example-data/bgpc_meta.yaml
