#include "Renderer.h"

#include "ArgParser.h"
#include "Camera.h"
#include "Image.h"
#include "Ray.h"
#include "VecUtils.h"
#include "Vector3f.h"
#include <random>

Renderer::Renderer(const ArgParser &args)
    : _args(args), _scene(args.input_file) {}

std::mt19937 rng(42);
std::uniform_real_distribution<float> dist(-1, 1);
void Renderer::Render() {
    int w = _args.width;
    int h = _args.height;

    if (_args.filter) {
        w *= 3;
        h *= 3;
    }

    Image cimage(w, h);
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
            // Jitter handling:
            // Perform jitter perturbation for the 3 images
            Vector3f totcolor, totnormal;
            float totdepth = 0.0f;
            if (_args.jitter) {
                for (int i = 0; i < 16; i++) {
                    float jx = dist(rng) / w;
                    float jy = dist(rng) / h ;
                    auto ray = cam->generateRay({ndcx + jx, ndcy + jy});
                    Hit hit;
                    totcolor +=
                        traceRay(ray, cam->getTMin(), _args.bounces, hit);
                    totdepth += hit.getT();
                    totnormal += (hit.getNormal() + 1.0f) / 2.0f;
                }
                totcolor /= 16;
                totnormal /= 16;
                totdepth /= 16;
            } else {
                Ray r = cam->generateRay(Vector2f(ndcx, ndcy));

                Hit h;
                totcolor = traceRay(r, cam->getTMin(), _args.bounces, h);
                totnormal = (h.getNormal() + 1.0f) / 2.0f;
                totdepth = h.getT();
            }

            cimage.setPixel(x, y, totcolor);
            nimage.setPixel(x, y, totnormal);
            dimage.setPixel(x, y, Vector3f((totdepth - _args.depth_min) / (_args.depth_max - _args.depth_min)));
        }
    }
    // Gaussian filtering
    if (_args.filter) {
        auto true_w = _args.width, true_h = _args.height;
        Image fcimage(true_w, true_h);
        Image fnimage(true_w, true_h);
        Image fdimage(true_w, true_h);

        // clang-format off
        auto fkernel = Matrix3f(
            1, 2, 1,
            2, 4, 2,
            1, 2, 1
        ) * (1.0f / 16.0f);
        // clang-format on
        for (int y = 0; y < true_h; y++) {
            for (int x = 0; x < true_w; x++) {
                Vector3f fcolor, fnormal, fdepth;
                for (int ki = 0; ki < 3; ki++) {
                    for (int kj = 0; kj < 3; kj++) {
                        fcolor += fkernel(ki, kj) * cimage.getPixel(3 * x + ki, 3 * y + kj);
                        fnormal += fkernel(ki, kj) * nimage.getPixel(3 * x + ki, 3 * y + kj);
                        fdepth += fkernel(ki, kj) * dimage.getPixel(3 * x + ki, 3 * y + kj);
                    }
                }
                fcimage.setPixel(x, y, fcolor);
                fnimage.setPixel(x, y, fnormal);
                fdimage.setPixel(x, y, fdepth);
            }
        }
        cimage = fcimage;
        nimage = fnimage;
        dimage = fdimage;
    }

    // save the files
    if (_args.output_file.size()) {
        cimage.savePNG(_args.output_file);
    }
    if (_args.depth_file.size()) {
        dimage.savePNG(_args.depth_file);
    }
    if (_args.normals_file.size()) {
        nimage.savePNG(_args.normals_file);
    }
}

Vector3f Renderer::traceRay(const Ray &r, float tmin, int bounces,
                            Hit &h) const {
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
        light->getIllumination(hitPoint, dirToLight, lightIntensity,
                               distToLight);
        Ray shadowRay(hitPoint + epsilon * dirToLight, dirToLight);
        Hit shadowHit;
        bool shadow =
            (_scene.getGroup()->intersect(shadowRay, epsilon, shadowHit) &&
             (std::isinf(distToLight) ||
              shadowHit.getT() < distToLight - epsilon));
        if (!shadow) {
            color += material->shade(r, h, dirToLight, lightIntensity);
        }
    }
    if (bounces > 0) {
        Vector3f specularColor = material->getSpecularColor();
        if (specularColor != Vector3f::ZERO) {
            Vector3f L = r.getDirection().normalized();
            Vector3f R =
                (L - 2.0f * Vector3f::dot(L, normal) * normal).normalized();
            Hit reflectHit;
            color += specularColor * traceRay(Ray(hitPoint + epsilon * R, R),
                                              tmin, bounces - 1, reflectHit);
        }
    }
    return color;
}
