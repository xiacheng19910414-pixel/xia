"""Exercise native image/contour dependencies for future image-based modeling."""
import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Polygon
from svgpathtools import parse_path
import pytest


def test_image_contour_svg_geometry_pipeline():
    image = Image.new('L',(64,64),0)
    ImageDraw.Draw(image).rectangle((8,8,55,55),fill=255)
    mask = np.array(image)
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    assert len(contours) == 1
    polygon = Polygon(contours[0].reshape(-1,2))
    assert polygon.is_valid and polygon.area == pytest.approx(47*47)
    assert distance_transform_edt(mask).max() == 24
    path = parse_path('M8,8 L55,8 L55,55 L8,55 Z')
    assert path.isclosed() and path.length() == pytest.approx(polygon.length)
