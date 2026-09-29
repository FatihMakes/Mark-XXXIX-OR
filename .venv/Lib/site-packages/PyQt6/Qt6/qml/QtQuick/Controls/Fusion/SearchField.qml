// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Fusion
import QtQuick.Controls.Fusion.impl

T.SearchField {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             searchIndicator.implicitIndicatorHeight + topPadding + bottomPadding)

    leftPadding: padding + (control.mirrored
                            ? (!clearIndicator.indicator || !clearIndicator.indicator.visible ? 0 : clearIndicator.indicator.width + spacing)
                            : (!searchIndicator.indicator || !searchIndicator.indicator.visible ? 0 : searchIndicator.indicator.width + spacing))
    rightPadding: padding + (control.mirrored
                             ? (!searchIndicator.indicator || !searchIndicator.indicator.visible ? 0 : searchIndicator.indicator.width + spacing)
                             : (!clearIndicator.indicator || !clearIndicator.indicator.visible ? 0 : clearIndicator.indicator.width + spacing))

    delegate: MenuItem {
        width: ListView.view.width
        text: model[control.textRole]
        font.weight: control.currentIndex === index ? Font.DemiBold : Font.Normal
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled

        required property var model
        required property int index
    }

    searchIndicator.indicator: PaddedRectangle {
        implicitWidth: 22
        implicitHeight: 20
        height: control.height - 2

        x: !control.mirrored ? 1 : control.width - width - 1
        y: 1

        radius: 1.7
        clip: true
        topPadding: -2
        leftPadding: -2

        color: control.searchIndicator.pressed ? Fusion.buttonColor(control.palette, false, true, true) : "transparent"

        ColorImage {
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            width: 18
            height: 18
            color: control.palette.buttonText
            source: "qrc:/qt-project.org/imports/QtQuick/Controls/Fusion/images/search-magnifier.png"
            opacity: enabled ? 1 : 0.3
        }
    }

    clearIndicator.indicator: PaddedRectangle {
        implicitWidth: 22
        implicitHeight: 20
        height: control.height - 2

        x: control.mirrored ? 1 : control.width - width - 1
        y: 1
        visible: control.text.length > 0

        radius: 1.7
        clip: true
        topPadding: -2
        leftPadding: -2

        color: control.clearIndicator.pressed ? Fusion.buttonColor(control.palette, false, true, true) : "transparent"

        ColorImage {
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            width: 18
            height: 18
            color: control.palette.buttonText
            source: "qrc:/qt-project.org/imports/QtQuick/Controls/Fusion/images/close_circle.png"
            opacity: enabled ? 1 : 0.3
        }
    }

    contentItem: T.TextField {
        implicitHeight: contentHeight + topPadding + bottomPadding

        leftPadding: !control.mirrored ? 6 : 0
        rightPadding: !control.mirrored ? 6 : 0

        text: control.text

        color: control.palette.text
        selectionColor: control.palette.highlight
        selectedTextColor: control.palette.highlightedText
        verticalAlignment: TextInput.AlignVCenter

        ContextMenu.menu: TextEditingContextMenu {
            editor: parent
        }
    }

    background: Rectangle {
        implicitWidth: 120
        implicitHeight: 24

        radius: 2
        color: control.palette.base
        border.color: control.activeFocus ? Fusion.highlightedOutline(control.palette) : Fusion.outline(control.palette)

        Rectangle {
            x: 1; y: 1
            width: parent.width - 2
            height: parent.height - 2
            color: "transparent"
            border.color: Color.transparent(Fusion.highlightedOutline(control.palette), 40 / 255)
            visible: control.activeFocus
            radius: 1.7
        }

        Rectangle {
            x: 2
            y: 1
            width: parent.width - 4
            height: 1
            color: Fusion.topShadow
        }

        Rectangle {
            x: !control.mirrored ? 1 : parent.width - width - 1
            y: 1
            width: control.searchIndicator.indicator && control.searchIndicator.indicator.visible
                   ? control.searchIndicator.indicator.width + 1  : 0
            height: parent.height - 2
            radius: 2

            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: Fusion.gradientStart(Fusion.buttonColor(control.palette, control.visualFocus, false, control.searchIndicator.hovered))
                }
                GradientStop {
                    position: 1
                    color: Fusion.gradientStop(Fusion.buttonColor(control.palette, control.visualFocus, false, control.searchIndicator.hovered))
                }
            }

            Rectangle {
                x: !control.mirrored ? parent.width - 1 : 0
                width: 1
                height: parent.height
                color: Fusion.outline(control.palette)
            }
        }

        Rectangle {
            x: control.mirrored ? 1 : parent.width - width - 1
            y: 1
            width: control.clearIndicator.indicator && control.clearIndicator.indicator.visible
                   ? control.clearIndicator.indicator.width + 1  : 0
            height: parent.height - 2
            radius: 2

            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: Fusion.gradientStart(Fusion.buttonColor(control.palette, control.visualFocus, false, control.clearIndicator.hovered))
                }
                GradientStop {
                    position: 1
                    color: Fusion.gradientStop(Fusion.buttonColor(control.palette, control.visualFocus, false, control.clearIndicator.hovered))
                }
            }

            Rectangle {
                x: control.mirrored ? parent.width - 1 : 0
                width: 1
                height: parent.height
                color: Fusion.outline(control.palette)
            }
        }
    }

    popup: T.Popup {
        y: control.height
        width: control.width
        height: Math.min(contentItem.implicitHeight, control.Window.height - control.y - control.height - control.padding)
        topMargin: 6
        bottomMargin: 6
        palette: control.palette

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            highlightMoveDuration: 0

            T.ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
            color: control.popup.palette.window
            border.color: Fusion.outline(control.palette)

            Rectangle {
                z: -1
                x: 1; y: 1
                width: parent.width
                height: parent.height
                color: control.palette.shadow
                opacity: 0.2
            }
        }
    }
}
