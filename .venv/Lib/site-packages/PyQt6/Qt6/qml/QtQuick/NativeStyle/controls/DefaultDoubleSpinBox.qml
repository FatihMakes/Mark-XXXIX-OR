// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls
import QtQuick.Templates as T
import QtQuick.NativeStyle as NativeStyle

T.DoubleSpinBox {
    id: control

    readonly property bool __nativeBackground: background instanceof NativeStyle.StyleItem
    readonly property bool __notCustomizable: true

    implicitWidth: Math.max(implicitBackgroundWidth + spacing + up.implicitIndicatorWidth
                            + leftInset + rightInset,
                            90 /* minimum */ )
    implicitHeight: Math.max(implicitBackgroundHeight, up.implicitIndicatorHeight + down.implicitIndicatorHeight
                    + (spacing * 3)) + topInset + bottomInset

    spacing: 2

    leftPadding: (__nativeBackground ? background.contentPadding.left: 0)
    topPadding: (__nativeBackground ? background.contentPadding.top: 0)
    rightPadding: (__nativeBackground ? background.contentPadding.right : 0) + up.implicitIndicatorWidth + spacing
    bottomPadding: (__nativeBackground ? background.contentPadding.bottom: 0) + spacing

    validator: DoubleValidator {
        locale: control.locale.name
        bottom: Math.min(control.from, control.to)
        top: Math.max(control.from, control.to)
        decimals: control.decimals
    }

    contentItem: TextInput {
        text: control.displayText
        color: control.palette.text
        selectionColor: control.palette.highlight
        selectedTextColor: control.palette.highlightedText
        horizontalAlignment: Qt.AlignLeft
        verticalAlignment: Qt.AlignVCenter

        topPadding: 2
        bottomPadding: 2
        leftPadding: 10
        rightPadding: 10

        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
    }

    up.indicator: NativeStyle.DoubleSpinBox {
        control: control
        subControl: NativeStyle.DoubleSpinBox.Up
        x: parent.width - width - spacing
        y: (parent.height / 2) - height
        useNinePatchImage: false
    }

    down.indicator: NativeStyle.DoubleSpinBox {
        control: control
        subControl: NativeStyle.DoubleSpinBox.Down
        x: up.indicator.x
        y: up.indicator.y + up.indicator.height
        useNinePatchImage: false
    }

    background: NativeStyle.DoubleSpinBox {
        control: control
        subControl: NativeStyle.DoubleSpinBox.Frame
        contentWidth: contentItem.implicitWidth
        contentHeight: contentItem.implicitHeight
    }
}
