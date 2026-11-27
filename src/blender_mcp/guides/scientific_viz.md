# Scientific and data visualisation

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). numpy is bundled with Blender (2.3.4 in 5.3).

## When to use

Turning data into 3D images or animations: surfaces z = f(x, y), terrain from elevation
grids, point clouds (lidar, particles, molecules, galaxies), volumes (CT/MRI, simulation
output as OpenVDB), meshes from scanners or solvers (PLY, OBJ, STL), graphs and 3D charts,
and time series as animation.

## Inputs needed

- The data files (CSV, NumPy-readable text, PLY, VDB, OBJ) inside the allowed directories,
  and their units and value ranges.
- What the viewer must read off the image: shape, magnitude (colour), change over time.
- Colour map (perceptually uniform: viridis, magma, cividis), legend and labels needed or
  not, and the output (still, turntable, time series).

## Workflow

1. Load data with plain Python/numpy (`numpy.loadtxt`, `csv`) or Blender importers
   (`wm.ply_import`, `wm.obj_import`, `wm.stl_import`, `object.volume_import` for VDB).
2. Build geometry with the data API and `foreach_set` (fast), not per-vertex loops.
3. Store values as attributes on the geometry; colour them in the material (Attribute ->
   Map Range -> Color Ramp), so the mapping can change without rebuilding geometry.
4. Scale: normalise to a few metres so lights, cameras and clipping work; note the factor.
5. Camera: orthographic for plots and maps (true proportions), perspective for spatial data.
6. Lighting: soft, neutral (sun plus world light); view transform Standard so colour maps
   stay accurate.
7. Add axes, labels and a legend if the image must be read quantitatively.
8. Render with EEVEE for speed; check with `look(mode="render")`.

## Tested values and code

```python
# [5.3] surface from data, values as an attribute, colour-mapped in the shader
import numpy as np, bmesh

me = bpy.data.meshes.new("Surface")
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=80, y_segments=80, size=2)
bm.to_mesh(me)
bm.free()
n = len(me.vertices)
co = np.empty(n * 3, dtype=np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(n, 3)
z = (np.sin(co[:, 0] * 2) * np.cos(co[:, 1] * 2) * 0.5).astype(np.float32)
co[:, 2] = z
me.vertices.foreach_set("co", co.ravel())
me.update()
me.attributes.new("value", "FLOAT", "POINT").data.foreach_set("value", z)

nt = mat.node_tree
bsdf = next(x for x in nt.nodes if x.type == "BSDF_PRINCIPLED")
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "value"  # GEOMETRY type
rng = nt.nodes.new("ShaderNodeMapRange")
rng.inputs["From Min"].default_value = -0.5
rng.inputs["From Max"].default_value = 0.5
ramp = nt.nodes.new("ShaderNodeValToRGB")
el = ramp.color_ramp.elements
el[0].color = (0.267, 0.005, 0.329, 1)
el[1].color = (0.993, 0.906, 0.144, 1)
el.new(0.5).color = (0.128, 0.567, 0.551, 1)  # viridis
nt.links.new(attr.outputs["Fac"], rng.inputs["Value"])
nt.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

# [5.3] point cloud object: resize, then write positions and radii
pc = bpy.data.pointclouds.new("Points")
pc.resize(len(pts))
pc.attributes["position"].data.foreach_set("vector", pts.astype(np.float32).ravel())
rad = pc.attributes.get("radius") or pc.attributes.new("radius", "FLOAT", "POINT")
rad.data.foreach_set("value", np.full(len(pts), 0.03, dtype=np.float32))
```

- Tested [5.3]: an 81 x 81 surface coloured by its attribute and 200 points rendered in
  EEVEE in about 1.5 s. Point cloud objects (`POINTCLOUD`) render in 5.3; they were
  experimental before 4.x [untested]. Fallback for older versions: a mesh of vertices
  with geometry-nodes Mesh to Points, or instanced spheres.
- `foreach_get`/`foreach_set` were ~14x faster than a Python loop on 3,721 vertices; the gap
  grows with size. Always use them for data.
- Shader Attribute types [5.3]: GEOMETRY, OBJECT, INSTANCER, VIEW_LAYER, LIGHT. Colour
  attributes: `mesh.color_attributes.new(name, "FLOAT_COLOR", "POINT")` (4.0+; earlier
  `vertex_colors`, untested).
- Importers in 5.3: `wm.ply_import`, `wm.obj_import`, `wm.stl_import`, `wm.usd_import`,
  `wm.alembic_import`, `wm.fbx_import`, plus `object.volume_import` for OpenVDB.
- Ortho camera: `cam.data.type = "ORTHO"`, `ortho_scale` = the width of the shown area.
- Time series: one frame per time step; keyframe values or swap geometry per frame with a
  geometry-nodes setup reading a frame-indexed attribute; drivers on `frame` for simple cases.

## Common mistakes

- Python loops over millions of points: minutes instead of milliseconds. Use numpy and
  foreach_set.
- Rainbow/jet colour maps: they invent edges in smooth data. Use viridis-like maps.
- AgX or Filmic view transforms shifting the colour map: use Standard for data.
- Data in kilometres or micrometres directly: clipping and lighting break. Normalise.
- Hard-coding the value range: compute min/max from the data, and show them in the legend.
- Perspective distortion on charts meant to be measured: use an orthographic camera.

## Verification checklist

- [ ] Point/vertex counts equal the data row counts; min/max of the attribute match the data.
- [ ] Colour map, range and legend agree; Standard view transform for accurate colours.
- [ ] Scale factor and units reported to the user; axes labelled if quantitative.
- [ ] `look(mode="render")` reads clearly at the delivery size.
- [ ] Time steps line up with frames (first, middle, last checked).

## Manual work and external tools

- Data cleaning and analysis belong in Python/Jupyter, ParaView, MATLAB or R before Blender.
- Specialised formats (NetCDF, HDF5, DICOM, PDB) need libraries Blender does not bundle;
  convert them to CSV, PLY or VDB outside Blender. Installing Python packages into
  Blender, and science add-ons (e.g. Molecular Nodes, BlenderGIS), are the user's call:
  safe execution mode refuses enabling add-ons and running external programs such as pip.
  Explain that and never bypass it.
- Scientific accuracy of the visual encoding should be reviewed by the user.
