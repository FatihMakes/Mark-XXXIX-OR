// This is the SIP interface definition for QAxObjectInterface.
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


class QAxObjectInterface
{
%TypeHeaderCode
#include <qaxobjectinterface.h>
%End

public:
    virtual unsigned long classContext() const = 0;
    virtual void setClassContext(unsigned long classContext) = 0;

    virtual QString control() const = 0;
    virtual bool setControl(const QString &c) = 0;
    virtual void resetControl() = 0;
};
