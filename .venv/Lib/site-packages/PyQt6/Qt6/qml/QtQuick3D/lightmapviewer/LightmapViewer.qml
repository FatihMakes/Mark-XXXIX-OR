// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import QtQuick3D
import QtQuick3D.Helpers

import QtQuick3D.lightmapviewer
import LightmapFile 1.0

ApplicationWindow {
    width: 1024
    height: 768
    visible: true
    title: qsTr("Lightmap Viewer")

    id: window

    property var selectedEntry: listView.model.length ? listView.model[0] : null
    property real imageZoom: 1
    property real imageCenterX: 0
    property real imageCenterY: 0

    function isImage(entry) {
        return entry && entry.kind === "image"
    }
    function isMesh(entry) {
        return entry && entry.kind === "mesh"
    }

    Dialog {
        id: sceneMetadataDialog
        modal: true
        standardButtons: Dialog.NoButton
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        visible: false
        width: 220
        height: 360

        contentItem: SceneMetadataView {}
    }

    header: ToolBar {
        RowLayout {
            Button {
                text: qsTr("Open Lightmap...")
                onClicked: fileDialog.open()
            }

            Rectangle {
                width: 1
                color: "darkgray"
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignVCenter
            }

            Button {
                text: qsTr("Scene Metadata...")
                onClicked: sceneMetadataDialog.open()
            }

            Label {
                text: "Zoom: " + window.imageZoom.toFixed(1)
            }

            Rectangle {
                width: 1
                color: "darkgray"
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignVCenter
            }

            Switch {
                id: alphaSwitch
                padding: 0
                checked: true
                text: "Alpha"
            }

            Rectangle {
                width: 1
                color: "darkgray"
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                text: "Path: " + LightmapFile.source
            }
        }
    }

    FileDialog {
        id: fileDialog
        onAccepted: {
            LightmapFile.source = selectedFile
            LightmapFile.loadData()
        }
    }

    Shortcut {
        sequences: [StandardKey.Open]
        onActivated: {
            fileDialog.open()
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        focus: true
        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Up) {
                                listView.currentIndex = Math.max(
                                    0, listView.currentIndex - 1)
                                selectedEntry = listView.model[listView.currentIndex]
                            } else if (event.key === Qt.Key_Down) {
                                listView.currentIndex = Math.min(
                                    listView.model.length - 1,
                                    listView.currentIndex + 1)
                                selectedEntry = listView.model[listView.currentIndex]
                            }
                        }

        SplitView {
            id: leftSplit
            SplitView.preferredWidth: 220
            SplitView.minimumWidth: 120
            orientation: Qt.Vertical

            Item {
                id: metaArea
                SplitView.preferredHeight: 120
                anchors.left: parent.left
                anchors.right: parent.right

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 4

                    Pane {
                        id: metaPane
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        ScrollView {
                            anchors.fill: parent

                            ColumnLayout {
                                id: metadataColumn
                                Layout.fillWidth: true
                                spacing: 4

                                Repeater {
                                    model: LightmapFile.metadataFor(selectedEntry)
                                    delegate: RowLayout {
                                        width: metadataColumn.width
                                        spacing: 8

                                        Label {
                                            text: (modelData.key ?? "—") + ":"
                                            font.bold: true
                                        }
                                        Label {
                                            text: modelData.value
                                                  !== undefined ? String(
                                                                      modelData.value) : "—"
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ListView {
                id: listView
                clip: true
                spacing: 2
                highlightMoveVelocity: -1
                highlightMoveDuration: 1
                model: LightmapFile.dataList
                property var sectionExpanded: ({})

                section.property: "owner"
                section.criteria: ViewSection.FullString
                section.delegate: Rectangle {
                    width: listView.width
                    height: 26
                    color: Qt.rgba(0, 0, 0, 0.05)
                    radius: 4

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            text: (listView.sectionExpanded[section] === false) ? "▸" : "▾"
                            verticalAlignment: Text.AlignVCenter
                        }
                        Text {
                            text: section
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            listView.sectionExpanded[section]
                                    = !(listView.sectionExpanded[section] !== false)
                            listView.sectionExpanded = Object.assign(
                                        {}, listView.sectionExpanded)
                        }
                    }
                }

                delegate: Item {
                    width: listView.width

                    property bool isExpanded: listView.sectionExpanded[modelData.owner] !== false

                    height: isExpanded ? Math.max(
                                             24, rowText.implicitHeight + 6) : 0
                    opacity: isExpanded ? 1 : 0

                    Behavior on height {
                        NumberAnimation {
                            duration: 120
                            easing.type: Easing.OutCubic
                        }
                    }
                    Behavior on opacity {
                        NumberAnimation {
                            duration: 120
                            easing.type: Easing.OutCubic
                        }
                    }

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            id: rowText
                            text: modelData.display
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: isExpanded
                        onClicked: {
                            listView.currentIndex = index
                            selectedEntry = modelData
                        }
                    }
                }

                highlight: Rectangle {
                    color: Qt.rgba(76 / 255, 134 / 255, 191 / 255, 0.25)
                    radius: 6
                    anchors.margins: 2
                }

                ScrollBar.vertical: ScrollBar {}
            }
        }

        Item {
            id: rightSplit
            SplitView.fillWidth: true
            SplitView.fillHeight: true

            // These are toggled based on what is currently selected
            Loader {
                id: imageLoader
                anchors.fill: parent
                sourceComponent: ImageViewer {}
                active: true
                visible: isImage(selectedEntry)
                enabled: visible
            }

            Loader {
                id: meshLoader
                anchors.fill: parent
                sourceComponent: MeshViewer {}
                active: true
                visible: isMesh(selectedEntry)
                enabled: visible
            }
        }
    }

    DropArea {
        id: dropArea
        anchors.fill: parent
        onEntered: drag => {
                       drag.accept(Qt.LinkAction)
                   }
        // Just take first url if several
        onDropped: drop => {
                       if (drop.hasUrls) {
                           LightmapFile.source = drop.urls[0]
                           LightmapFile.loadData()
                       }
                   }
    }
}
