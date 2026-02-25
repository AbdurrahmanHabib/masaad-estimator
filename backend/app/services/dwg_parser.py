import os
import subprocess
import ezdxf
from ezdxf.math import BoundingBox
from shapely.geometry import Polygon, MultiPolygon
from typing import List, Dict, Any

class DWGParserService:
    def __init__(self, oda_converter_path: str):
        self.oda_path = oda_converter_path

    def convert_dwg_to_dxf(self, input_path: str, output_dir: str) -> str:
        filename = os.path.basename(input_path)
        dxf_filename = filename.replace(".dwg", ".dxf")
        input_dir = os.path.dirname(input_path)
        
        try:
            subprocess.run([
                self.oda_path, input_dir, output_dir, 
                "ACAD2018", "DXF", "0", "1"
            ], check=True, capture_output=True)
            return os.path.join(output_dir, dxf_filename)
        except subprocess.CalledProcessError as e:
            raise Exception(f"ODA Conversion Failed: {e.stderr.decode()}")

    def extract_geometry(self, dxf_path: str) -> Dict[str, Any]:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        layers_data = {}

        for insert in msp.query('INSERT'):
            layer = insert.dxf.layer
            if layer not in layers_data: layers_data[layer] = {"blocks": [], "areas": []}
            block = doc.blocks.get(insert.dxf.name)
            bbox = BoundingBox(block.query('LINE LWPOLYLINE CIRCLE HATCH'))
            layers_data[layer]["blocks"].append({
                "name": insert.dxf.name,
                "position": (insert.dxf.insert.x, insert.dxf.insert.y),
                "width": bbox.size.x * insert.dxf.xscale,
                "height": bbox.size.y * insert.dxf.yscale,
                "rotation": insert.dxf.rotation
            })

        layer_polygons = {}
        for entity in msp.query('LWPOLYLINE HATCH'):
            layer = entity.dxf.layer
            if layer not in layer_polygons: layer_polygons[layer] = []
            if entity.dxftype() == 'LWPOLYLINE':
                points = [(p[0], p[1]) for p in entity.get_points()]
                if len(points) >= 3: layer_polygons[layer].append(Polygon(points))
            elif entity.dxftype() == 'HATCH':
                for path in entity.paths:
                    points = [(p[0], p[1]) for p in path.vertices]
                    if len(points) >= 3: layer_polygons[layer].append(Polygon(points))

        for layer, polygons in layer_polygons.items():
            if layer not in layers_data: layers_data[layer] = {"blocks": [], "areas": []}
            sorted_polys = sorted(polygons, key=lambda p: p.area, reverse=True)
            for i, poly in enumerate(sorted_polys):
                current_poly = poly
                for j in range(i + 1, len(sorted_polys)):
                    inner_poly = sorted_polys[j]
                    if current_poly.contains(inner_poly):
                        current_poly = current_poly.difference(inner_poly)
                layers_data[layer]["areas"].append({
                    "net_area": current_poly.area / 1e6,
                    "bounds": current_poly.bounds,
                    "is_complex": isinstance(current_poly, MultiPolygon)
                })
        return layers_data