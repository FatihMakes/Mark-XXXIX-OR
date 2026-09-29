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

ColumnLayout {
    id: root
    anchors.fill: parent

    property string selectedModelCandidate: ""

    onSelectedModelCandidateChanged: {
        if (!selectedModelCandidate || selectedModelCandidate === "") {
            view.lmTextureCandidates = []
            lview.mSelectedTextureCandidate = -1
            return
        }
        view.lmTextureCandidates = LightmapFile.texturesAvailableFor(
                    selectedModelCandidate)
        view.lmSelectedTextureCandidate
                = view.lmTextureCandidates.length ? view.lmTextureCandidates[0].value : -1
    }

    Pane {
        Layout.fillWidth: true
        padding: 8

        ColumnLayout {
            width: parent.width
            spacing: 6

            ColumnLayout {
                RowLayout {
                    Label {
                        text: "Key:"
                    }
                    ComboBox {
                        id: comboLmModelCandidate
                        Layout.preferredWidth: 220
                        model: view.lmModelCandidates
                        onActivated: root.selectedModelCandidate = currentText
                        currentIndex: {
                            const i = view.lmModelCandidates.indexOf(
                                        root.selectedModelCandidate)
                            return (i >= 0 ? i : -1)
                        }
                        enabled: !!selectedEntry
                                 && selectedEntry.kind === "mesh"
                    }
                    Label {
                        text: "Texture:"
                    }
                    ComboBox {
                        id: comboLmTextureCandidate
                        Layout.preferredWidth: 220
                        model: view.lmTextureCandidates
                        textRole: "name"
                        valueRole: "value"

                        function indexForValue(val) {
                            for (var i = 0; i < view.lmTextureCandidates.length; ++i)
                                if (view.lmTextureCandidates[i].value === val)
                                    return i
                            return -1
                        }

                        onActivated: view.lmSelectedTextureCandidate = Number(
                                         currentValue)
                        currentIndex: indexForValue(
                                          view.lmSelectedTextureCandidate)
                        enabled: !!selectedEntry
                                 && selectedEntry.kind === "mesh"
                    }
                }

                RowLayout {
                    CheckBox {
                        id: checkboxBfCull
                        text: "Backface Culling"
                        checked: true
                    }
                    CheckBox {
                        id: checkboxDebugUV
                        text: "Debug UV"
                        checked: false
                    }
                }
            }
        }
    }

    View3D {
        id: view
        Layout.fillWidth: true
        Layout.fillHeight: true
        enabled: meshLoader.visible
        visible: meshLoader.visible

        property var lmModelCandidates: []
        property var lmTextureCandidates: []
        property int lmSelectedTextureCandidate: -1

        property real boundsDiameter: 0
        property vector3d boundsCenter
        property vector3d boundsSize

        function updateBounds(bounds) {
            boundsSize = Qt.vector3d(bounds.maximum.x - bounds.minimum.x,
                                     bounds.maximum.y - bounds.minimum.y,
                                     bounds.maximum.z - bounds.minimum.z)
            boundsDiameter = Math.max(boundsSize.x, boundsSize.y, boundsSize.z)
            boundsCenter = Qt.vector3d(
                        (bounds.maximum.x + bounds.minimum.x) / 2,
                        (bounds.maximum.y + bounds.minimum.y) / 2,
                        (bounds.maximum.z + bounds.minimum.z) / 2)
            model.position = Qt.vector3d(-boundsCenter.x, -boundsCenter.y,
                                         -boundsCenter.z)
            cameraNode.clipNear = boundsDiameter / 100
            cameraNode.clipFar = boundsDiameter * 10
            resetCamera()
        }

        function resetCamera() {
            cameraNode.position = boundsCenter
            cameraNode.position = Qt.vector3d(0, 0, 2 * boundsDiameter)
            cameraNode.eulerRotation = Qt.vector3d(0, 0, 0)
        }

        function refreshLightmapSelection() {
            if (!selectedEntry) {
                lmModelCandidates = []
                root.selectedModelCandidate = ""
                lmTextureCandidates = []
                lmSelectedTextureCandidate = -1
                return
            }

            if (selectedEntry.kind === "image") {
                lmModelCandidates = [selectedEntry.key]
                root.selectedModelCandidate = selectedEntry.key
            } else if (selectedEntry.kind === "mesh") {
                lmModelCandidates = LightmapFile.keysReferencingMesh(
                            selectedEntry.key)
                root.selectedModelCandidate = lmModelCandidates.length ? lmModelCandidates[0] : ""
            } else {
                lmModelCandidates = []
                root.selectedModelCandidate = ""
                lmTextureCandidates = []
                lmSelectedTextureCandidate = -1
            }
        }

        Component.onCompleted: refreshLightmapSelection()
        Connections {
            target: window
            function onSelectedEntryChanged() {
                view.refreshLightmapSelection()
            }
        }

        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: "black"
        }

        PerspectiveCamera {
            id: cameraNode
            z: 300
        }

        Node {
            id: modelNode

            Model {
                id: model
                geometry: LightmapMesh {
                    source: LightmapFile.source
                    key: selectedEntry.key
                    onBoundsChanged: view.updateBounds(bounds)
                }
                materials: CustomMaterial {
                    shadingMode: CustomMaterial.Unshaded
                    cullMode: checkboxBfCull.checked ? Material.BackFaceCulling : Material.NoCulling

                    property TextureInput baseMap: TextureInput {
                        texture: Texture {
                            id: lmTexture
                            minFilter: Texture.Linear
                            magFilter: Texture.Linear
                            mipFilter: Texture.None
                            tilingModeHorizontal: Texture.ClampToEdge
                            tilingModeVertical: Texture.ClampToEdge

                            textureData: LightmapFile.textureDataFor(
                                             root.selectedModelCandidate,
                                             view.lmSelectedTextureCandidate)
                        }
                    }
                    property bool debugUV: checkboxDebugUV.checked

                    vertexShader: "mesh.vert"
                    fragmentShader: "mesh.frag"
                }
            }
        }

        ArcballController {
            id: arcballController
            controlledObject: modelNode

            function jumpToAxis(axis) {
                cameraRotation.from = arcballController.controlledObject.rotation
                cameraRotation.to = originGizmo.quaternionForAxis(
                            axis, arcballController.controlledObject.rotation)
                cameraRotation.duration = 200
                cameraRotation.start()
            }

            function jumpToRotation(qRotation) {
                cameraRotation.from = arcballController.controlledObject.rotation
                cameraRotation.to = qRotation
                cameraRotation.duration = 100
                cameraRotation.start()
            }

            QuaternionAnimation {
                id: cameraRotation
                target: arcballController.controlledObject
                property: "rotation"
                type: QuaternionAnimation.Slerp
                running: false
                loops: 1
            }
        }

        OriginGizmo {
            id: originGizmo
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 10
            width: 120
            height: 120
            targetNode: modelNode

            onAxisClicked: axis => {
                               arcballController.jumpToAxis(axis)
                           }
        }

        DragHandler {
            id: dragHandler
            target: null
            acceptedModifiers: Qt.NoModifier
            onCentroidChanged: {
                arcballController.mouseMoved(toNDC(centroid.position.x,
                                                   centroid.position.y))
            }

            onActiveChanged: {
                if (active) {
                    view.forceActiveFocus()
                    arcballController.mousePressed(toNDC(centroid.position.x,
                                                         centroid.position.y))
                } else
                    arcballController.mouseReleased(toNDC(centroid.position.x,
                                                          centroid.position.y))
            }

            function toNDC(x, y) {
                return Qt.vector2d((2.0 * x / width) - 1.0,
                                   1.0 - (2.0 * y / height))
            }
        }

        WheelHandler {
            id: wheelHandler
            orientation: Qt.Vertical
            target: null
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            onWheel: event => {
                         let delta = -event.angleDelta.y * 0.01
                         cameraNode.z += cameraNode.z * 0.1 * delta
                     }
        }

        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Space) {
                                let rotation = originGizmo.quaternionAlign(
                                    arcballController.controlledObject.rotation)
                                arcballController.jumpToRotation(rotation)
                            } else if (event.key === Qt.Key_S) {
                                settingsPane.toggleHide()
                            } else if (event.key === Qt.Key_Left
                                       || event.key === Qt.Key_A) {
                                let rotation = originGizmo.quaternionRotateLeft(
                                    arcballController.controlledObject.rotation)
                                arcballController.jumpToRotation(rotation)
                            } else if (event.key === Qt.Key_Right
                                       || event.key === Qt.Key_D) {
                                let rotation = originGizmo.quaternionRotateRight(
                                    arcballController.controlledObject.rotation)
                                arcballController.jumpToRotation(rotation)
                            }
                        }
    }
}
