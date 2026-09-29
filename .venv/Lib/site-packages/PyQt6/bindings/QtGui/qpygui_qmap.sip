// This is the SIP interface definition for the QMap mapped types specific to
// QtGui.
//
// Copyright (c) 2026 Riverbank Computing Limited <info@riverbankcomputing.com>
// 
// This file is part of PyQt6.
// 
// This file may be used under the terms of the GNU General Public License
// version 3.0 as published by the Free Software Foundation and appearing in
// the file LICENSE included in the packaging of this file.  Please review the
// following information to ensure the GNU General Public License version 3.0
// requirements will be met: http://www.gnu.org/copyleft/gpl.html.
// 
// If you do not wish to use this file under the terms of the GPL version 3.0
// then you may purchase a commercial license.  For more information contact
// info@riverbankcomputing.com.
// 
// This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
// WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.


%If (Qt_6_11_0 -)

template<_TYPE_, quint32>
%MappedType QMap<_TYPE_, quint32>
        /TypeHint="Dict[_TYPE_, int]", TypeHintValue="{}"/
{
%TypeHeaderCode
#include <qfont.h>
#include <qmap.h>
%End

%ConvertFromTypeCode
    PyObject *d = PyDict_New();

    if (!d)
        return 0;

    QMap<_TYPE_, quint32>::const_iterator it = sipCpp->constBegin();
    QMap<_TYPE_, quint32>::const_iterator end = sipCpp->constEnd();

    while (it != end)
    {
        _TYPE_ *k = new _TYPE_(it.key());
        PyObject *kobj = sipConvertFromNewType(k, sipType__TYPE_,
                sipTransferObj);

        if (!kobj)
        {
            delete k;
            Py_DECREF(d);

            return 0;
        }

        PyObject *vobj = PyLong_FromUnsignedLong(it.value());

        if (!vobj)
        {
            Py_DECREF(kobj);
            Py_DECREF(d);

            return 0;
        }

        int rc = PyDict_SetItem(d, kobj, vobj);

        Py_DECREF(vobj);
        Py_DECREF(kobj);

        if (rc < 0)
        {
            Py_DECREF(d);

            return 0;
        }

        ++it;
    }

    return d;
%End

%ConvertToTypeCode
    if (!sipIsErr)
        return PyDict_Check(sipPy);

    QMap<_TYPE_, quint32> *qm = new QMap<_TYPE_, quint32>;

    Py_ssize_t pos = 0;
    PyObject *kobj, *vobj;
 
    while (PyDict_Next(sipPy, &pos, &kobj, &vobj))
    {
        int kstate;
        _TYPE_ *k = reinterpret_cast<_TYPE_ *>(
                sipForceConvertToType(kobj, sipType__TYPE_, sipTransferObj,
                        SIP_NOT_NONE, &kstate, sipIsErr));

        if (*sipIsErr)
        {
            PyErr_Format(PyExc_TypeError,
                    "a dict key has type '%s' but '_TYPE_' is expected",
                    sipPyTypeName(Py_TYPE(kobj)));

            delete qm;

            return 0;
        }

        quint32 v = sipLong_AsUnsignedInt(vobj);

        if (PyErr_Occurred())
        {
            if (PyErr_ExceptionMatches(PyExc_TypeError))
                PyErr_Format(PyExc_TypeError,
                        "a dict value has type '%s' but 'int' is expected",
                        sipPyTypeName(Py_TYPE(vobj)));

            delete qm;
            *sipIsErr = 1;

            return 0;
        }

        qm->insert(*k, v);

        sipReleaseType(k, sipType__TYPE_, kstate);
    }
 
    *sipCppPtr = qm;
 
    return sipGetState(sipTransferObj);
%End
};


template<_TYPE_, float>
%MappedType QMap<_TYPE_, float>
        /TypeHint="Dict[_TYPE_, float]", TypeHintValue="{}"/
{
%TypeHeaderCode
#include <qfont.h>
#include <qmap.h>
%End

%ConvertFromTypeCode
    PyObject *d = PyDict_New();

    if (!d)
        return 0;

    QMap<_TYPE_, float>::const_iterator it = sipCpp->constBegin();
    QMap<_TYPE_, float>::const_iterator end = sipCpp->constEnd();

    while (it != end)
    {
        _TYPE_ *k = new _TYPE_(it.key());
        PyObject *kobj = sipConvertFromNewType(k, sipType__TYPE_,
                sipTransferObj);

        if (!kobj)
        {
            delete k;
            Py_DECREF(d);

            return 0;
        }

        PyObject *vobj = PyFloat_FromDouble(it.value());

        if (!vobj)
        {
            Py_DECREF(kobj);
            Py_DECREF(d);

            return 0;
        }

        int rc = PyDict_SetItem(d, kobj, vobj);

        Py_DECREF(vobj);
        Py_DECREF(kobj);

        if (rc < 0)
        {
            Py_DECREF(d);

            return 0;
        }

        ++it;
    }

    return d;
%End

%ConvertToTypeCode
    if (!sipIsErr)
        return PyDict_Check(sipPy);

    QMap<_TYPE_, float> *qm = new QMap<_TYPE_, float>;

    Py_ssize_t pos = 0;
    PyObject *kobj, *vobj;
 
    while (PyDict_Next(sipPy, &pos, &kobj, &vobj))
    {
        int kstate;
        _TYPE_ *k = reinterpret_cast<_TYPE_ *>(
                sipForceConvertToType(kobj, sipType__TYPE_, sipTransferObj,
                        SIP_NOT_NONE, &kstate, sipIsErr));

        if (*sipIsErr)
        {
            PyErr_Format(PyExc_TypeError,
                    "a dict key has type '%s' but '_TYPE_' is expected",
                    sipPyTypeName(Py_TYPE(kobj)));

            delete qm;

            return 0;
        }

        float v = PyFloat_AsDouble(vobj);

        if (PyErr_Occurred())
        {
            if (PyErr_ExceptionMatches(PyExc_TypeError))
                PyErr_Format(PyExc_TypeError,
                        "a dict value has type '%s' but 'float' is expected",
                        sipPyTypeName(Py_TYPE(vobj)));

            delete qm;
            *sipIsErr = 1;

            return 0;
        }

        qm->insert(*k, v);

        sipReleaseType(k, sipType__TYPE_, kstate);
    }
 
    *sipCppPtr = qm;
 
    return sipGetState(sipTransferObj);
%End
};

%End
