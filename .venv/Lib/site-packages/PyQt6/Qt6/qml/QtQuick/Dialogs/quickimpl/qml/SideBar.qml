// Copyright (C) 2024 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Dialogs.quickimpl as DialogsQuickImpl

DialogsQuickImpl.SideBar {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    contentWidth: (contentItem as ListView)?.contentWidth

    background: Rectangle {
        color: control.palette.window
    }

    contentItem: ListView {
        id: listView
        currentIndex: control.currentIndex
        model: control.contentModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {}
    }

    buttonDelegate: Button {
        id: buttonDelegateRoot

        required property int index
        required property string folderName

        flat: true
        highlighted: control.currentIndex === index
        width: listView.width
        text: folderName
        spacing: 5
        icon.color: highlighted ? palette.highlightedText : palette.text
        contentItem: IconLabel {
            leftPadding: 10
            topPadding: 3
            bottomPadding: 3
            alignment: Qt.AlignLeft
            spacing: buttonDelegateRoot.spacing
            icon: buttonDelegateRoot.icon
            text: buttonDelegateRoot.text
            font: buttonDelegateRoot.font
            defaultIconColor: buttonDelegateRoot.icon.color
            color: defaultIconColor
        }
        background: DelegateBackground {
            control: buttonDelegateRoot
        }
    }

    separatorDelegate: Item {
        implicitWidth: control.width
        implicitHeight: 9
        Rectangle {
            id: separatorDelegate
            color: Qt.lighter(control.palette.dark, 1.06)
            anchors.centerIn: parent
            radius: 1
            height: 1
            width: parent.width - 10
        }
    }

    addFavoriteDelegate: Button {
        id: addFavoriteDelegateRoot

        required property string labelText
        required property bool dragHovering

        flat: true
        width: control.width
        spacing: 5
        icon.color: highlighted ? palette.highlightedText : palette.text
        contentItem: IconLabel {
            leftPadding: 10
            topPadding: 3
            bottomPadding: 3
            alignment: Qt.AlignLeft
            spacing: addFavoriteDelegateRoot.spacing
            icon: addFavoriteDelegateRoot.icon
            text: addFavoriteDelegateRoot.labelText
            font: addFavoriteDelegateRoot.font
            defaultIconColor: addFavoriteDelegateRoot.icon.color
            color: defaultIconColor
            opacity: addFavoriteDelegateRoot.dragHovering ? 0.2 : 1.0
        }

        background: DelegateBackground {
            control: addFavoriteDelegateRoot
        }
    }
}
