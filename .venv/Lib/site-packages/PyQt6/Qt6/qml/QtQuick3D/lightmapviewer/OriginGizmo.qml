// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0
import QtQuick
import QtQuick3D

Item {
    id: root
    required property Node targetNode

    enum Axis {
        PositiveZ = 0,
        NegativeZ = 1,
        PositiveY = 2,
        NegativeY = 3,
        PositiveX = 4,
        NegativeX = 5
    }

    // These are the 24 different rotations a rotation aligned on axes can have.
    // They are ordered in groups of 4 where the +Z,-Z,+Y,-Y,+X,-X axis is pointing
    // towards the screen (+Z). Inside this group the rotations are ordered to
    // rotate counter-clockwise.
    readonly property list<quaternion> rotations: [
        // +Z
        Qt.quaternion(1, 0, 0, 0),
        Qt.quaternion(Math.SQRT1_2, 0, 0, -Math.SQRT1_2),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(Math.SQRT1_2, 0, 0, Math.SQRT1_2),
        // -Z
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -Math.SQRT1_2, -Math.SQRT1_2, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, Math.SQRT1_2, -Math.SQRT1_2, 0),
        // +Y
        Qt.quaternion(0.5, 0.5, 0.5, 0.5),
        Qt.quaternion(Math.SQRT1_2, Math.SQRT1_2, 0, 0),
        Qt.quaternion(-0.5, -0.5, 0.5, 0.5),
        Qt.quaternion(0, 0, -Math.SQRT1_2, -Math.SQRT1_2),
        // -Y
        Qt.quaternion(0.5, -0.5, 0.5, -0.5),
        Qt.quaternion(0, 0, Math.SQRT1_2, -Math.SQRT1_2),
        Qt.quaternion(-0.5, 0.5, 0.5, -0.5),
        Qt.quaternion(-Math.SQRT1_2, Math.SQRT1_2, 0, 0),
        // +X
        Qt.quaternion(-0.5, -0.5, 0.5, -0.5),
        Qt.quaternion(-Math.SQRT1_2, 0, Math.SQRT1_2, 0),
        Qt.quaternion(-0.5, 0.5, 0.5, 0.5),
        Qt.quaternion(0, Math.SQRT1_2, 0, Math.SQRT1_2),
        // -X
        Qt.quaternion(0, Math.SQRT1_2, 0, -Math.SQRT1_2),
        Qt.quaternion(0.5, -0.5, 0.5, 0.5),
        Qt.quaternion(Math.SQRT1_2, 0, Math.SQRT1_2, 0),
        Qt.quaternion(0.5, 0.5, 0.5, -0.5),
    ]

    readonly property list<quaternion> xRotationGoals : [
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(-0, -1, -0, -0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(-0, -1, -0, -0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(-0, 1, -0, -0),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
    ]

    readonly property list<quaternion>  yRotationGoals : [
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
    ]

    readonly property list<quaternion>  zRotationGoals : [
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, 1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 0, 0, -1),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 0, -1, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, -1, 0, 0),
        Qt.quaternion(0, 0, 1, 0),
        Qt.quaternion(0, 1, 0, 0),
        Qt.quaternion(0, 0, -1, 0),
    ]

    // This function works by using a rotation to rotate x,y,z normal vectors
    // and see what axis-aligned rotation gives the closest distance to the
    // rotated normal vectors.
    function findClosestRotation(rotation, startI, stopI) {
        let rotationConjugated = rotation.conjugated();
        let xRotated = rotation.times(Qt.quaternion(0, 1, 0, 0)).times(rotationConjugated);
        let yRotated = rotation.times(Qt.quaternion(0, 0, 1, 0)).times(rotationConjugated);
        let zRotated = rotation.times(Qt.quaternion(0, 0, 0, 1)).times(rotationConjugated);

        var closestIndex = 0;
        var closestDistance = 123456789; // big number

        for (var i = startI; i < stopI ; i++) {
            let distance = xRotated.minus(xRotationGoals[i]).length() +
                           yRotated.minus(yRotationGoals[i]).length() +
                           zRotated.minus(zRotationGoals[i]).length();
            if (distance <= closestDistance) {
                closestDistance = distance;
                closestIndex = i;
            }
        }

        return closestIndex;
    }

    function quaternionAlign(rotation) {
        let closestIndex = findClosestRotation(rotation, 0, 24);
        return rotations[closestIndex];
    }

    function quaternionForAxis(axis, rotation) {
        let closestIndex = findClosestRotation(rotation, axis*4, (axis + 1)*4);
        return rotations[closestIndex];
    }

    function quaternionRotateLeft(rotation) {
        let closestIndex = findClosestRotation(rotation, 0, 24);
        let offset = (4 + closestIndex - 1) % 4;
        let group = Math.floor(closestIndex / 4);
        return rotations[offset + group * 4];
    }

    function quaternionRotateRight(rotation) {
        let closestIndex = findClosestRotation(rotation, 0, 24);
        let offset = (closestIndex + 1) % 4;
        let group = Math.floor(closestIndex / 4);
        return rotations[offset + group * 4];
    }

    signal axisClicked(int axis)
    signal ballMoved(vector2d velocity)

    QtObject {
        id: stylePalette
        property color white: "#fdf6e3"
        property color black: "#002b36"
        property color red: "#dc322f"
        property color green: "#859900"
        property color blue: "#268bd2"
        property color background: "#99002b36"
    }

    component LineRectangle : Rectangle {
        property vector2d startPoint: Qt.vector2d(0, 0)
        property vector2d endPoint: Qt.vector2d(0, 0)
        property real lineWidth: 5
        transformOrigin: Item.Left
        height: lineWidth

        readonly property vector2d offset: startPoint.plus(endPoint).times(0.5);

        width: startPoint.minus(endPoint).length()
        rotation: Math.atan2(endPoint.y - startPoint.y, endPoint.x - startPoint.x) * 180 / Math.PI
    }


    Rectangle {
        id: ballBackground
        anchors.centerIn: parent
        width: parent.width > parent.height ? parent.height : parent.width
        height: width
        radius: width / 2
        color: ballBackgroundHoverHandler.hovered ? stylePalette.background : "transparent"

        readonly property real subBallWidth: width / 5
        readonly property real subBallHalfWidth: subBallWidth * 0.5
        readonly property real subBallOffset: radius - subBallWidth / 2

        Item {
            anchors.centerIn: parent

            component SubBall : Rectangle {
                id: subBallRoot
                required property Node targetNode
                required property real offset

                property alias labelText: label.text
                property alias labelColor: label.color
                property alias labelVisible: label.visible
                property alias hovered: subBallHoverHandler.hovered
                property var initialPosition: Qt.vector3d(0, 0, 0)
                readonly property vector3d position: quaternionVectorMultiply(targetNode.rotation, initialPosition)

                signal tapped()

                function quaternionVectorMultiply(q, v) {
                    var qv = Qt.vector3d(q.x, q.y, q.z)
                    var uv = qv.crossProduct(v)
                    var uuv = qv.crossProduct(uv)
                    uv = uv.times(2.0 * q.scalar)
                    uuv = uuv.times(2.0)
                    return v.plus(uv).plus(uuv)
                }

                height: width
                radius: width / 2
                x: offset * position.x - width / 2
                y: offset * -position.y - height / 2
                z: position.z

                HoverHandler {
                    id: subBallHoverHandler
                }

                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onTapped: (eventPoint, button)=>{
                        subBallRoot.tapped()
                        //eventPoint.accepted = true
                    }
                }

                Text {
                    id: label
                    anchors.centerIn: parent
                }
            }

            SubBall {
                id: positiveX
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "X"
                labelColor: hovered ? stylePalette.white : stylePalette.black
                color: stylePalette.red
                initialPosition: Qt.vector3d(1, 0, 0)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.PositiveX)
                }
            }

            LineRectangle {
                endPoint: Qt.vector2d(positiveX.x + ballBackground.subBallHalfWidth, positiveX.y + ballBackground.subBallHalfWidth)
                color: stylePalette.red
                z: positiveX.z - 0.001
            }

            SubBall {
                id: positiveY
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "Y"
                labelColor: hovered ? stylePalette.white : stylePalette.black
                color: stylePalette.green
                initialPosition: Qt.vector3d(0, 1, 0)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.PositiveY)
                }
            }

            LineRectangle {
                endPoint: Qt.vector2d(positiveY.x + ballBackground.subBallHalfWidth, positiveY.y + ballBackground.subBallHalfWidth)
                color: stylePalette.green
                z: positiveY.z - 0.001
            }

            SubBall {
                id: positiveZ
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "Z"
                labelColor: hovered ? stylePalette.white : stylePalette.black
                color: stylePalette.blue
                initialPosition: Qt.vector3d(0, 0, 1)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.PositiveZ)
                }
            }

            LineRectangle {
                endPoint: Qt.vector2d(positiveZ.x + ballBackground.subBallHalfWidth, positiveZ.y + ballBackground.subBallHalfWidth)
                color: stylePalette.blue
                z: positiveZ.z - 0.001
            }

            SubBall {
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "-X"
                labelColor: stylePalette.white
                labelVisible: hovered
                color: Qt.rgba(stylePalette.red.r, stylePalette.red.g, stylePalette.red.b, z + 1 * 0.5)
                border.color: stylePalette.red
                border.width: 2
                initialPosition: Qt.vector3d(-1, 0, 0)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.NegativeX)
                }
            }

            SubBall {
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "-Y"
                labelColor: stylePalette.white
                labelVisible: hovered
                color: Qt.rgba(stylePalette.green.r, stylePalette.green.g, stylePalette.green.b, z + 1 * 0.5)
                border.color: stylePalette.green
                border.width: 2
                initialPosition: Qt.vector3d(0, -1, 0)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.NegativeY)
                }
            }

            SubBall {
                targetNode: root.targetNode
                width: ballBackground.subBallWidth
                offset: ballBackground.subBallOffset
                labelText: "-Z"
                labelColor: stylePalette.white
                labelVisible: hovered
                color: Qt.rgba(stylePalette.blue.r, stylePalette.blue.g, stylePalette.blue.b, z + 1 * 0.5)
                border.color: stylePalette.blue
                border.width: 2
                initialPosition: Qt.vector3d(0, 0, -1)
                onTapped: {
                    root.axisClicked(OriginGizmo.Axis.NegativeZ)
                }
            }
        }

        HoverHandler {
            id: ballBackgroundHoverHandler
            acceptedDevices: PointerDevice.Mouse
            cursorShape: Qt.PointingHandCursor
        }

        DragHandler {
            id: dragHandler
            target: null
            enabled: ballBackground.visible
            onCentroidChanged: {
                if (centroid.velocity.x > 0 && centroid.velocity.y > 0) {
                    root.ballMoved(centroid.velocity)
                }
            }
        }
    }
}
