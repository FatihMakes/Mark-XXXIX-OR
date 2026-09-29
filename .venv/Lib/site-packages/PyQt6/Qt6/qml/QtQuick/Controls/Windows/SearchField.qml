// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.impl
import QtQuick.Templates as T
import QtQuick.NativeStyle as NativeStyle
import QtQuick.Controls.Windows.impl

NativeStyle.DefaultSearchField {
    id: control

    readonly property bool __nativeSearchIndicator: searchIndicator.indicator.hasOwnProperty("_qt_default")
    readonly property bool __nativeClearIndicator: clearIndicator.indicator.hasOwnProperty("_qt_default")

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding,
                            90 /* minimum */ )
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             searchIndicator.implicitIndicatorHeight + topPadding + bottomPadding,
                             clearIndicator.implicitIndicatorHeight + topPadding + bottomPadding)

    contentItem: T.TextField {
        text: control.text

        color: control.palette.text
        selectionColor: control.palette.highlight
        selectedTextColor: control.palette.highlightedText
        verticalAlignment: Text.AlignVCenter

        readonly property bool __ignoreNotCustomizable: true

        ContextMenu.menu: TextEditingContextMenu {
            editor: parent
        }
    }

    NativeStyle.SearchField {
        id: search
        visible: control.__nativeSearchIndicator
        control: control
        subControl: NativeStyle.SearchField.Search
        x: searchIndicator.indicator.x
        y: searchIndicator.indicator.y
        useNinePatchImage: false
    }

    searchIndicator.indicator: Item {
        x: 3
        y: control.topPadding + (control.availableHeight - height) / 2
        implicitWidth: search.width
        implicitHeight: search.height

        property bool _qt_default
        readonly property bool __ignoreNotCustomizable: true

        ColorImage {
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            width: 12
            height: 12

            source: Qt.resolvedUrl("images/search-magnifier")
            color: control.palette.buttonText
            opacity: control.searchIndicator.pressed ? 0.7 : 1
        }
    }

    NativeStyle.SearchField {
        id: clear
        visible: control.__nativeClearIndicator && control.text.length > 0
        control: control
        subControl: NativeStyle.SearchField.Clear
        x: clearIndicator.indicator.x
        y: clearIndicator.indicator.y
        useNinePatchImage: false
    }

    clearIndicator.indicator: Item {
        x: control.width - width - 3
        y: control.topPadding + (control.availableHeight - height) / 2
        implicitWidth: clear.width
        implicitHeight: clear.height

        property bool _qt_default
        readonly property bool __ignoreNotCustomizable: true

        ColorImage {
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            width: 12
            height: 12

            source: Qt.resolvedUrl("images/close_big")
            visible: control.text.length > 0
            color: control.palette.buttonText
            opacity: control.clearIndicator.pressed ? 0.7 : 1
        }
    }

    background: NativeStyle.SearchField {
        control: control
        subControl: NativeStyle.SearchField.Frame
        contentWidth: contentItem.implicitWidth
        contentHeight: contentItem.implicitHeight

        readonly property bool __ignoreNotCustomizable: true
    }
}
