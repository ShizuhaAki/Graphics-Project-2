#include "Renderer.h"

#include "ArgParser.h"
#include "Camera.h"
#include "Image.h"
#include "Ray.h"
#include "VecUtils.h"
#include "Vector3f.h"

#include <limits>

Renderer::Renderer(const ArgParser &args)
    : _args(args), _scene(args.input_file) {}

void Renderer::Render() {
    int w = _args.width;
    int h = _args.height;

    Image image(w, h);
    Image nimage(w, h);
    Image dimage(w, h);

    // loop through all the pixels in the image
    // generate all the samples

    // This look generates camera rays and callse traceRay.
    // It also write to the color, normal, and depth images.
    // You should understand what this code does.
    Camera *cam = _scene.getCamera();
    for (int y = 0; y < h; ++y) {
        float ndcy = 2 * (y / (h - 1.0f)) - 1.0f;
        for (int x = 0; x < w; ++x) {
            float ndcx = 2 * (x / (w - 1.0f)) - 1.0f;
            // Use PerspectiveCamera to generate a ray.
            // You should understand what generateRay() does.
            Ray r = cam->generateRay(Vector2f(ndcx, ndcy));

            Hit h;
            Vector3f color = traceRay(r, cam->getTMin(), _args.bounces, h);

            image.setPixel(x, y, color);
            if (h.getMaterial() != nullptr) {
                nimage.setPixel(x, y, (h.getNormal() + 1.0f) / 2.0f);
                float range = (_args.depth_max - _args.depth_min);
                if (range) {
                    dimage.setPixel(
                        x, y, Vector3f((h.t - _args.depth_min) / range));
                }
            } else {
                nimage.setPixel(x, y, Vector3f::ZERO);
                dimage.setPixel(x, y, Vector3f::ZERO);
            }
    
            /* Vector3f n = h.getNormal();
            if ((n + Vector3f(1, 1, 1)).absSquared() < 1e-6) {
                std::cerr << "Black!!!: (" << x << ", " << y << "): " << n << std::endl;
            } */
        }
    }
    // END SOLN

    // save the files
    if (_args.output_file.size()) {
        image.savePNG(_args.output_file);
    }
    if (_args.depth_file.size()) {
        dimage.savePNG(_args.depth_file);
    }
    if (_args.normals_file.size()) {
        nimage.savePNG(_args.normals_file);
    }
}

Vector3f Renderer::traceRay(const Ray &r, float tmin, int bounces, Hit &h) const {
    // std::cerr << tmin << " " << bounces << "\n";
    if (!_scene.getGroup()->intersect(r, tmin, h)) {
        return _scene.getBackgroundColor(r.getDirection());
    }
    const auto material = h.getMaterial();
    Vector3f color = _scene.getAmbientLight() * material->getDiffuseColor();
    const auto hitPoint = r.pointAtParameter(h.getT());
    const auto normal = h.getNormal().normalized();
    constexpr static float epsilon = 1e-4f;
    for (auto light : _scene.lights) {
        Vector3f dirToLight, lightIntensity;
        float distToLight;
        light->getIllumination(hitPoint, dirToLight, lightIntensity, distToLight);
        Ray shadowRay(hitPoint + epsilon * dirToLight, dirToLight);
        Hit shadowHit;
        bool shadow = (
            _scene.getGroup()->intersect(shadowRay, epsilon, shadowHit) && (
                std::isinf(distToLight) || shadowHit.getT() < distToLight - epsilon
            )
        );
        if (!shadow) {
            color += material->shade(r, h, dirToLight, lightIntensity);
        }
    }
    if (bounces > 0) {
        Vector3f specularColor = material->getSpecularColor();
        if (specularColor != Vector3f::ZERO) {
            Vector3f L = r.getDirection().normalized();
            Vector3f R = (L - 2.0f * Vector3f::dot(L, normal) * normal).normalized();
            Hit reflectHit;
            color += specularColor * traceRay(Ray(hitPoint + epsilon * R, R), tmin, bounces - 1, reflectHit);
        }
    }
    return color;
}
