// This is the SIP interface definition for QAxWidget.
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


class QAxBaseWidget : QWidget, QAxObjectInterface
{
%TypeHeaderCode
#include <qaxwidget.h>
%End

signals:
    void exception(int code, const QString &source, const QString &desc, const QString &help);
    void propertyChanged(const QString &name);
    void signal(const QString &name, int argc, void *argv);
};


class QAxWidget : QAxBaseWidget, QAxBase
{
%TypeHeaderCode
#include <qaxwidget.h>
%End

public:
    explicit QAxWidget(QWidget *parent /TransferThis/ = 0, Qt::WindowFlags flags = Qt::WindowFlags());
    explicit QAxWidget(const QString &, QWidget *parent /TransferThis/ = 0,
            Qt::WindowFlags flags = Qt::WindowFlags());
    //explicit QAxWidget(IUnknown *, QWidget *parent /TransferThis/ = 0, Qt::WindowFlags flags = Qt::WindowFlags());
    ~QAxWidget();

    unsigned long classContext() const;
    void setClassContext(unsigned long classContext);

    QString control() const;
    bool setControl(const QString &c);
    void resetControl();

    void clear();
    bool doVerb(const QString &);

    QSize sizeHint() const;
    QSize minimumSizeHint() const;

    //virtual QaxAggregated *createAggregate();

protected:
    //bool initialize(IUnknown **);
    virtual bool createHostWindow(bool);
    bool createHostWindow(bool, const QByteArray &);

    void changeEvent(QEvent *);
    void resizeEvent(QResizeEvent *);

    virtual bool translateKeyEvent(int,int) const;

    void connectNotify(const QMetaMethod &);
};
