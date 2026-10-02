"""Kapalı ağı kenar daraltma ile hedef üçgen sayısına indirir, en büyük parçayı tutar.
python scripts/decimate.py girdi.stl çıktı.stl 600000"""
import sys, pymeshlab, trimesh
src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
ms = pymeshlab.MeshSet(); ms.load_new_mesh(src)
ms.meshing_remove_connected_component_by_diameter(mincomponentdiag=pymeshlab.PercentageValue(2))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=n, preservenormal=True, preservetopology=True, qualitythr=0.4, optimalplacement=True)
ms.save_current_mesh(out)
m = trimesh.load(out)
print(out, len(m.faces), 'watertight', m.is_watertight, 'vol', round(m.volume, 1))
