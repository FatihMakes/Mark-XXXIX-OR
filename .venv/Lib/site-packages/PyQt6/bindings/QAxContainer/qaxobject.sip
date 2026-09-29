// This is the SIP interface definition for QAxObject.
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


class QAxBaseObject : QObject, QAxObjectInterface
{
%TypeHeaderCode
#include <qaxobject.h>
%End

signals:
    void exception(int code, const QString &source, const QString &desc, const QString &help);
    void propertyChanged(const QString &name);
    void signal(const QString &name, int argc, void *argv);
};


class QAxObject : QAxBaseObject, QAxBase
{
%TypeHeaderCode
#include <qaxobject.h>
%End

public:
    explicit QAxObject(QObject *parent /TransferThis/ = 0);
    explicit QAxObject(const QString &, QObject *parent /TransferThis/ = 0);
    //explicit QAxObject(IUnknown *, QObject *parent /TransferThis/ = 0);
    ~QAxObject();

%ConvertToSubClassCode
    static struct class_graph {
        const char *name;
        sipTypeDef **type;
        int yes, no;
    } graph[] = {
        {sipName_QAxBaseObject, &sipType_QAxBaseObject, 2, 1},
        {sipName_QAxBaseWidget, &sipType_QAxBaseWidget, 3, -1},
        {sipName_QAxObject, &sipType_QAxObject, -1, -1},
        {sipName_QAxWidget, &sipType_QAxWidget, -1, -1},
    };

    int i = 0;

    sipType = NULL;

    do
    {
        struct class_graph *cg = &graph[i];

        if (cg->name != NULL && sipCpp->inherits(cg->name))
        {
            sipType = *cg->type;
            i = cg->yes;
        }
        else
            i = cg->no;
    }
    while (i >= 0);
%End

    unsigned long classContext() const;
    void setClassContext(unsigned long classContext);

    QString control() const;
    bool setControl(const QString &c);
    void resetControl();

    void clear();
    bool doVerb(const QString &);

protected:
    void connectNotify(const QMetaMethod &);
};
