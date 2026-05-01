#include "Object3D.h"
#include "Matrix3f.h"
#include "Vector3f.h"
#include "Vector4f.h"

bool Sphere::intersect(const Ray &r, float tmin, Hit &h) const {
    // BEGIN STARTER

    // We provide sphere intersection code for you.
    // You should model other intersection implementations after this one.

    // Locate intersection point ( 2 pts )
    const Vector3f &rayOrigin =
        r.getOrigin(); // Ray origin in the world coordinate
    const Vector3f &dir = r.getDirection();

    Vector3f origin = rayOrigin - _center; // Ray origin in the sphere
                                           // coordinate

    float a = dir.absSquared();
    float b = 2 * Vector3f::dot(dir, origin);
    float c = origin.absSquared() - _radius * _radius;

    // no intersection
    if (b * b - 4 * a * c < 0) {
        return false;
    }

    float d = sqrt(b * b - 4 * a * c);

    float tplus = (-b + d) / (2.0f * a);
    float tminus = (-b - d) / (2.0f * a);

    // the two intersections are at the camera back
    if ((tplus < tmin) && (tminus < tmin)) {
        return false;
    }

    float t = 10000;
    // the two intersections are at the camera front
    if (tminus > tmin) {
        t = tminus;
    }

    // one intersection at the front. one at the back
    if ((tplus > tmin) && (tminus < tmin)) {
        t = tplus;
    }

    if (t < h.getT()) {
        Vector3f normal = r.pointAtParameter(t) - _center;
        normal = normal.normalized();
        h.set(t, this->material, normal);
        return true;
    }
    // END STARTER
    return false;
}

// Add object to group
void Group::addObject(Object3D *obj) { m_members.push_back(obj); }

// Return number of objects in group
int Group::getGroupSize() const { return (int)m_members.size(); }

bool Group::intersect(const Ray &r, float tmin, Hit &h) const {
    // BEGIN STARTER
    // we implemented this for you
    bool hit = false;
    for (Object3D *o : m_members) {
        if (o->intersect(r, tmin, h)) {
            hit = true;
        }
    }
    return hit;
    // END STARTER
}

Plane::Plane(const Vector3f &normal, float d, Material *m)
    : Object3D(m), _d(d), _n(normal) {}
bool Plane::intersect(const Ray &r, float tmin, Hit &h) const {
    float direction = Vector3f::dot(r.getDirection(), _n);
    if (std::abs(direction) < 1e-8)
        return false;
    float t = Vector3f::dot(_n * _d - r.getOrigin(), _n) / direction;
    if (t <= tmin || t >= h.getT())
        return false;
    h.set(t, material, _n);
    return true;
}
bool Triangle::intersect(const Ray &r, float tmin, Hit &h) const {
    auto edge1 = _v[1] - _v[0], edge2 = _v[2] - _v[0];
    /* Vector3f faceDir = Vector3f::cross(edge1, edge2);
    if (Vector3f::dot(r.getDirection(), faceDir) > 0) {
        return false;
    } */
    
    Matrix3f A(-r.getDirection(), edge1, edge2);
    bool singular = false;
    Matrix3f invA = A.inverse(&singular, 1e-8f);
    if (singular) {
        return false;
    }
    Vector3f x = invA * (r.getOrigin() - _v[0]);
    float t = x[0];
    float u = x[1];
    float v = x[2];
    if (u < 0 || u > 1) {
        return false;
    }
    if (v < 0 || u + v > 1) {
        return false;
    }
    if (t <= tmin || t >= h.getT()) {
        return false;
    }
    float w = 1 - u - v;
    // auto n = (Vector3f::cross(edge1, edge2)).normalized();
    auto n = (w * _normals[0] + u * _normals[1] + v * _normals[2]).normalized();
    h.set(t, material, n);
    return true;
}

Transform::Transform(const Matrix4f &m, Object3D *obj) : _object(obj),  m(m) {}
bool Transform::intersect(const Ray &r, float tmin, Hit &h) const {
    bool singular = false;
    auto minv = m.inverse(&singular, 1e-8f);
    assert(!singular);
    /* if (singular) {
        return false;
    } */

    auto newOrigin = (minv * Vector4f(r.getOrigin(), 1.0f)).xyz();
    auto newDirection = (minv * Vector4f(r.getDirection(), 0.0f)).xyz();
    Ray newRay{newOrigin, newDirection};

    Hit hit;
    if (!_object->intersect(newRay, tmin, hit)) {
        return false;
    }

    Vector3f Q = (
        m * Vector4f(newRay.pointAtParameter(hit.getT()), 1.0f)
    ).xyz();

    const auto rO = r.getOrigin(), rD = r.getDirection();
    const float T = Vector3f::dot(Q - rO, rD) / rD.absSquared();

    if (T <= tmin || T >= h.getT()) {
        return false;
    }

    auto newNormal = (
        minv.getSubmatrix3x3(0, 0).transposed() * hit.getNormal()
    ).normalized();
    h.set(hit.getT(), hit.getMaterial(), newNormal);
    // h.set(T, hit.getMaterial(), newNormal);
    return true;
}
