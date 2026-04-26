#include "Material.h"
#include "Vector3f.h"
Vector3f Material::shade(const Ray &ray, const Hit &hit,
                         const Vector3f &dirToLight,
                         const Vector3f &lightIntensity)

{
    auto l = dirToLight.normalized();
    auto v = (-ray.getDirection()).normalized(); // toward camera
    auto n = hit.getNormal().normalized();
    auto r = ((-l) - 2.0f * Vector3f::dot(-l, n) * n).normalized();
    auto diffuse =
        std::max(0.0f, Vector3f::dot(l, n)) * _diffuseColor * lightIntensity;
    auto specular = std::pow(std::max(0.0f, Vector3f::dot(v, r)), _shininess) *
                    _specularColor * lightIntensity;
    return diffuse + specular;
}
