__all__: list[str] = []

import cv2
import cv2.typing
import typing as _typing


# Enumerations
CCM_LINEAR: int
CCM_AFFINE: int
CcmType = int
"""One of [CCM_LINEAR, CCM_AFFINE]"""

INITIAL_METHOD_WHITE_BALANCE: int
INITIAL_METHOD_LEAST_SQUARE: int
InitialMethodType = int
"""One of [INITIAL_METHOD_WHITE_BALANCE, INITIAL_METHOD_LEAST_SQUARE]"""

COLORCHECKER_MACBETH: int
COLORCHECKER_VINYL: int
COLORCHECKER_DIGITAL_SG: int
ColorCheckerType = int
"""One of [COLORCHECKER_MACBETH, COLORCHECKER_VINYL, COLORCHECKER_DIGITAL_SG]"""

COLOR_SPACE_SRGB: int
COLOR_SPACE_SRGBL: int
COLOR_SPACE_ADOBE_RGB: int
COLOR_SPACE_ADOBE_RGBL: int
COLOR_SPACE_WIDE_GAMUT_RGB: int
COLOR_SPACE_WIDE_GAMUT_RGBL: int
COLOR_SPACE_PRO_PHOTO_RGB: int
COLOR_SPACE_PRO_PHOTO_RGBL: int
COLOR_SPACE_DCI_P3_RGB: int
COLOR_SPACE_DCI_P3_RGBL: int
COLOR_SPACE_APPLE_RGB: int
COLOR_SPACE_APPLE_RGBL: int
COLOR_SPACE_REC_709_RGB: int
COLOR_SPACE_REC_709_RGBL: int
COLOR_SPACE_REC_2020_RGB: int
COLOR_SPACE_REC_2020_RGBL: int
COLOR_SPACE_XYZ_D65_2: int
COLOR_SPACE_XYZ_D50_2: int
COLOR_SPACE_XYZ_D65_10: int
COLOR_SPACE_XYZ_D50_10: int
COLOR_SPACE_XYZ_A_2: int
COLOR_SPACE_XYZ_A_10: int
COLOR_SPACE_XYZ_D55_2: int
COLOR_SPACE_XYZ_D55_10: int
COLOR_SPACE_XYZ_D75_2: int
COLOR_SPACE_XYZ_D75_10: int
COLOR_SPACE_XYZ_E_2: int
COLOR_SPACE_XYZ_E_10: int
COLOR_SPACE_LAB_D65_2: int
COLOR_SPACE_LAB_D50_2: int
COLOR_SPACE_LAB_D65_10: int
COLOR_SPACE_LAB_D50_10: int
COLOR_SPACE_LAB_A_2: int
COLOR_SPACE_LAB_A_10: int
COLOR_SPACE_LAB_D55_2: int
COLOR_SPACE_LAB_D55_10: int
COLOR_SPACE_LAB_D75_2: int
COLOR_SPACE_LAB_D75_10: int
COLOR_SPACE_LAB_E_2: int
COLOR_SPACE_LAB_E_10: int
ColorSpace = int
"""One of [COLOR_SPACE_SRGB, COLOR_SPACE_SRGBL, COLOR_SPACE_ADOBE_RGB, COLOR_SPACE_ADOBE_RGBL, COLOR_SPACE_WIDE_GAMUT_RGB, COLOR_SPACE_WIDE_GAMUT_RGBL, COLOR_SPACE_PRO_PHOTO_RGB, COLOR_SPACE_PRO_PHOTO_RGBL, COLOR_SPACE_DCI_P3_RGB, COLOR_SPACE_DCI_P3_RGBL, COLOR_SPACE_APPLE_RGB, COLOR_SPACE_APPLE_RGBL, COLOR_SPACE_REC_709_RGB, COLOR_SPACE_REC_709_RGBL, COLOR_SPACE_REC_2020_RGB, COLOR_SPACE_REC_2020_RGBL, COLOR_SPACE_XYZ_D65_2, COLOR_SPACE_XYZ_D50_2, COLOR_SPACE_XYZ_D65_10, COLOR_SPACE_XYZ_D50_10, COLOR_SPACE_XYZ_A_2, COLOR_SPACE_XYZ_A_10, COLOR_SPACE_XYZ_D55_2, COLOR_SPACE_XYZ_D55_10, COLOR_SPACE_XYZ_D75_2, COLOR_SPACE_XYZ_D75_10, COLOR_SPACE_XYZ_E_2, COLOR_SPACE_XYZ_E_10, COLOR_SPACE_LAB_D65_2, COLOR_SPACE_LAB_D50_2, COLOR_SPACE_LAB_D65_10, COLOR_SPACE_LAB_D50_10, COLOR_SPACE_LAB_A_2, COLOR_SPACE_LAB_A_10, COLOR_SPACE_LAB_D55_2, COLOR_SPACE_LAB_D55_10, COLOR_SPACE_LAB_D75_2, COLOR_SPACE_LAB_D75_10, COLOR_SPACE_LAB_E_2, COLOR_SPACE_LAB_E_10]"""

LINEARIZATION_IDENTITY: int
LINEARIZATION_GAMMA: int
LINEARIZATION_COLORPOLYFIT: int
LINEARIZATION_COLORLOGPOLYFIT: int
LINEARIZATION_GRAYPOLYFIT: int
LINEARIZATION_GRAYLOGPOLYFIT: int
LinearizationType = int
"""One of [LINEARIZATION_IDENTITY, LINEARIZATION_GAMMA, LINEARIZATION_COLORPOLYFIT, LINEARIZATION_COLORLOGPOLYFIT, LINEARIZATION_GRAYPOLYFIT, LINEARIZATION_GRAYLOGPOLYFIT]"""

DISTANCE_CIE76: int
DISTANCE_CIE94_GRAPHIC_ARTS: int
DISTANCE_CIE94_TEXTILES: int
DISTANCE_CIE2000: int
DISTANCE_CMC_1TO1: int
DISTANCE_CMC_2TO1: int
DISTANCE_RGB: int
DISTANCE_RGBL: int
DistanceType = int
"""One of [DISTANCE_CIE76, DISTANCE_CIE94_GRAPHIC_ARTS, DISTANCE_CIE94_TEXTILES, DISTANCE_CIE2000, DISTANCE_CMC_1TO1, DISTANCE_CMC_2TO1, DISTANCE_RGB, DISTANCE_RGBL]"""



# Classes
class ColorCorrectionModel:
    # Functions
    @_typing.overload
    def __init__(self) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.typing.MatLike, constColor: int) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.UMat, constColor: int) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.typing.MatLike, colors: cv2.typing.MatLike, refColorSpace: ColorSpace) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.UMat, colors: cv2.UMat, refColorSpace: ColorSpace) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.typing.MatLike, colors: cv2.typing.MatLike, refColorSpace: ColorSpace, coloredPatchesMask: cv2.typing.MatLike) -> None: ...
    @_typing.overload
    def __init__(self, src: cv2.UMat, colors: cv2.UMat, refColorSpace: ColorSpace, coloredPatchesMask: cv2.UMat) -> None: ...

    def setColorSpace(self, cs: ColorSpace) -> None: ...

    def setCcmType(self, ccmType: CcmType) -> None: ...

    def setDistance(self, distance: DistanceType) -> None: ...

    def setLinearization(self, linearizationType: LinearizationType) -> None: ...

    def setLinearizationGamma(self, gamma: float) -> None: ...

    def setLinearizationDegree(self, deg: int) -> None: ...

    def setSaturatedThreshold(self, lower: float, upper: float) -> None: ...

    def setWeightsList(self, weightsList: cv2.typing.MatLike) -> None: ...

    def setWeightCoeff(self, weightsCoeff: float) -> None: ...

    def setInitialMethod(self, initialMethodType: InitialMethodType) -> None: ...

    def setMaxCount(self, maxCount: int) -> None: ...

    def setEpsilon(self, epsilon: float) -> None: ...

    def setRGB(self, rgb: bool) -> None: ...

    def compute(self) -> cv2.typing.MatLike: ...

    def getColorCorrectionMatrix(self) -> cv2.typing.MatLike: ...

    def getLoss(self) -> float: ...

    def getSrcLinearRGB(self) -> cv2.typing.MatLike: ...

    def getRefLinearRGB(self) -> cv2.typing.MatLike: ...

    def getMask(self) -> cv2.typing.MatLike: ...

    def getWeights(self) -> cv2.typing.MatLike: ...

    @_typing.overload
    def correctImage(self, src: cv2.typing.MatLike, dst: cv2.typing.MatLike | None = ..., islinear: bool = ...) -> cv2.typing.MatLike: ...
    @_typing.overload
    def correctImage(self, src: cv2.UMat, dst: cv2.UMat | None = ..., islinear: bool = ...) -> cv2.UMat: ...

    def write(self, fs: cv2.FileStorage) -> None: ...

    def read(self, node: cv2.FileNode) -> None: ...



# Functions
@_typing.overload
def gammaCorrection(src: cv2.typing.MatLike, gamma: float, dst: cv2.typing.MatLike | None = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def gammaCorrection(src: cv2.UMat, gamma: float, dst: cv2.UMat | None = ...) -> cv2.UMat: ...


