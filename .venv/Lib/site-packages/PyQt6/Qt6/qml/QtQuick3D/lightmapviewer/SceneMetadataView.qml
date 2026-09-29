// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import LightmapFile 1.0

Item {
    id: root
    implicitWidth: 360
    implicitHeight: 420

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            anchors.fill: parent
            spacing: 6

            Label {
                text: `Baked with Qt version: ${LightmapFile.qtVersion || "—"}`
                font.bold: true
                Layout.fillWidth: true
            }

            Label {
                text: LightmapFile.bakeStart
                visible: text.length > 0
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                Component.onCompleted: if (text.length)
                                           text = "Bake initiated at:\n" + text
            }

            Label {
                text: LightmapFile.bakeDuration
                visible: text.length > 0
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Component.onCompleted: if (text.length)
                                           text = "Bake took:\n" + text
            }

            Label {
                text: "Options used:"
                Layout.fillWidth: true
            }

            ColumnLayout {
                id: optionsColumn
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: LightmapFile.options
                    delegate: RowLayout {
                        width: optionsColumn.width
                        spacing: 8

                        Label {
                            text: (modelData.key ?? "—") + ":"
                            font.bold: true
                            Layout.preferredWidth: 150
                            Layout.alignment: Qt.AlignRight | Qt.AlignTop
                            elide: Text.ElideRight
                        }
                        Label {
                            text: modelData.value !== undefined ? String(
                                                                      modelData.value) : "—"
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Item {
                width: 1
                height: 6
            }
        }
    }
}
