# PJ2 实验报告

完成者：尚书 / 阚子淳

## 光线投射

光线投射的第一步是把屏幕上的二维像素映射到相机成像平面。`Render()` 中先将像素坐标归一化到 `[-1, 1]` 的 NDC 区间，再调用 `PerspectiveCamera::generateRay()` 生成从相机中心出发的透视投影光线。这里使用的是标准针孔相机模型：由视场角计算像平面距离，再把视线方向、上方向和水平方向线性组合，得到当前像素对应的三维射线方向。

主光线生成后，程序调用场景中物体组的 `intersect` 接口寻找最近交点。如果射线没有命中任何物体，函数就返回背景颜色；如果命中物体，便取得交点材质、交点位置和表面法线，进入着色阶段。这里的直接光照实现采用了 Phong 模型。环境光部分使用场景环境光与材质漫反射颜色相乘，保证阴影区域仍有基础亮度。对于每个光源，`Material::shade()` 分别计算 Lambert 漫反射和镜面反射，再与环境光项相加得到局部着色结果。

这里我们需要实现不同几何体的 `intersect` 逻辑。对于平面，使用 $P \cdot n = d$ 的平面方程求出射线参数 $t$，再判断它是否落在可见范围内。对于三角形，实现中将交点写成重心坐标形式，并通过求解线性方程组判断交点是否位于三角形内部；在得到合法交点后，再用重心坐标对三个顶点法线做插值，从而得到更平滑的法线图结果。对于球体，则直接求解射线与二次曲面的交点。

这里我们还需要实现 `Transform` 类，这里，没有把子对象真的变换到世界坐标下再做后续判定，因为对于网格这类包含大量顶点的复杂对象，这样做的代价太高。代码中的做法是先求出 $M$ 的逆矩阵 $M^{-1}$，再用它把世界坐标下的射线原点和方向分别变换到局部对象坐标中。这样构造出的新射线就可以直接交给子对象已有的 `intersect` 函数处理，不需要为变换额外重写求交逻辑。得到局部空间中的命中结果后，再把交点对应的法线变换回世界坐标。这里按照 PJ1 中的做法，使用变换矩阵逆的转置来处理法线，也就是对 $M^{-1}$ 的左上角 $3\times 3$ 子矩阵取转置后再作用到法线上，最后归一化。
## 光线追踪

如果材质具有镜面反射分量且 `bounces > 0`，程序会根据入射方向和法线计算反射方向，并递归发射反射光线。递归返回的颜色乘以镜面系数后叠加到当前像素，从而形成真正依赖场景环境的反射效果，而不只是局部高光。最大递归深度由 `-bounces` 控制，因此可以在渲染质量和时间开销之间做平衡。

在引入光线追踪后，就需要进一步修改光照模型，加上一个间接光的项。也就是最终得到的光照为

$$
\mathrm{total = (ambient + Lambertian + shininess) \> + specular \times indirect}
$$


接着，我们需要实现阴影投射的逻辑。它需要在计算颜色（`shade`）前动作。对于已经命中的表面，程序会继续向每个光源发射 shadow ray，判断光源与交点之间是否存在遮挡；若有遮挡，该光源对当前点的直接光照贡献就被忽略。为了避免阴影光线与当前表面立即发生自相交，射线起点沿出射方向额外偏移了一个很小的 `epsilon = 1e-4`。这一步让场景中的遮挡关系能够真实反映到最终图像上，防止它和自己相交产生伪影。

## 抗锯齿问题

### 抖动采样
我们不再对每个像素只取中心样本，而是在该像素附近随机扰动出 16 条主光线，并分别追踪它们的颜色、法线和深度，再对结果取平均。这样，几何边缘会被平滑，从而有效减轻硬边锯齿。与规则网格采样相比，随机抖动还能避免一些结构化采样误差，让高频边缘不容易出现明显的摩尔纹。

### 高斯滤波
程序先把渲染分辨率在横纵方向都放大 3 倍，也就是在更细的网格上计算颜色图、法线图和深度图，然后对每个目标像素取其对应 `3×3` 邻域，使用高斯分布得到的权重 kernel

$$
\frac{1}{16}
\begin{bmatrix}
1 & 2 & 1 \\
2 & 4 & 2 \\
1 & 2 & 1
\end{bmatrix}
$$

做卷积，最后得到降采样后的结果图。

## 渲染结果

### Scene 01 Plane

<p align="center">
  <a href="ui/runs/a01_custom.png"><img src="ui/runs/a01_custom.png" width="31%"></a>
  <a href="ui/runs/a01_custom_depth.png"><img src="ui/runs/a01_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a01_custom_normals.png"><img src="ui/runs/a01_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 02 Cube

<p align="center">
  <a href="ui/runs/a02_custom.png"><img src="ui/runs/a02_custom.png" width="31%"></a>
  <a href="ui/runs/a02_custom_depth.png"><img src="ui/runs/a02_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a02_custom_normals.png"><img src="ui/runs/a02_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 03 Sphere

<p align="center">
  <a href="ui/runs/a03_custom.png"><img src="ui/runs/a03_custom.png" width="31%"></a>
  <a href="ui/runs/a03_custom_depth.png"><img src="ui/runs/a03_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a03_custom_normals.png"><img src="ui/runs/a03_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 04 Axes

<p align="center">
  <a href="ui/runs/a04_custom.png"><img src="ui/runs/a04_custom.png" width="31%"></a>
  <a href="ui/runs/a04_custom_depth.png"><img src="ui/runs/a04_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a04_custom_normals.png"><img src="ui/runs/a04_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 05 Bunny 200

<p align="center">
  <a href="ui/runs/a05_custom.png"><img src="ui/runs/a05_custom.png" width="31%"></a>
  <a href="ui/runs/a05_custom_depth.png"><img src="ui/runs/a05_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a05_custom_normals.png"><img src="ui/runs/a05_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 06 Bunny 1K

<p align="center">
  <a href="ui/runs/a06_custom.png"><img src="ui/runs/a06_custom.png" width="31%"></a>
  <a href="ui/runs/a06_custom_depth.png"><img src="ui/runs/a06_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a06_custom_normals.png"><img src="ui/runs/a06_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

### Scene 07 Arch

<p align="center">
  <a href="ui/runs/a07_custom.png"><img src="ui/runs/a07_custom.png" width="31%"></a>
  <a href="ui/runs/a07_custom_depth.png"><img src="ui/runs/a07_custom_depth.png" width="31%"></a>
  <a href="ui/runs/a07_custom_normals.png"><img src="ui/runs/a07_custom_normals.png" width="31%"></a>
</p>
<p align="center">左：颜色图；中：深度图；右：法线图。</p>

## 总结

本次实验从相机模型、主光线求交和 Phong 着色出发，完成了一个可输出颜色、法线和深度结果的基础光线投射器；再通过阴影光线与镜面递归反射，把它扩展为具备更真实光照关系的光线追踪渲染器；最后又通过 16 次随机抖动采样与 3 倍超采样后的高斯滤波，缓解了锯齿问题。