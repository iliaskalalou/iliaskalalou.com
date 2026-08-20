// Person cutout using macOS Vision. Usage: cutout <in.jpg> <out.png>
import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else { FileHandle.standardError.write("usage: cutout <in> <out>\n".data(using:.utf8)!); exit(2) }
guard let src = CIImage(contentsOf: URL(fileURLWithPath: args[1])) else { print("ERR: cannot read input"); exit(1) }

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8

let handler = VNImageRequestHandler(ciImage: src, options: [:])
do { try handler.perform([req]) } catch { print("ERR: \(error)"); exit(1) }

guard let obs = req.results?.first, let buf = obs.pixelBuffer as CVPixelBuffer? else { print("ERR: no person found"); exit(1) }

var mask = CIImage(cvPixelBuffer: buf)
let sx = src.extent.width / mask.extent.width
let sy = src.extent.height / mask.extent.height
mask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))

let blend = CIFilter(name: "CIBlendWithMask")!
blend.setValue(src, forKey: kCIInputImageKey)
blend.setValue(CIImage(color: .clear).cropped(to: src.extent), forKey: kCIInputBackgroundImageKey)
blend.setValue(mask, forKey: kCIInputMaskImageKey)
guard let out = blend.outputImage else { print("ERR: blend failed"); exit(1) }

let ctx = CIContext()
guard let cg = ctx.createCGImage(out, from: src.extent) else { print("ERR: raster failed"); exit(1) }
let rep = NSBitmapImageRep(cgImage: cg)
guard let png = rep.representation(using: .png, properties: [:]) else { print("ERR: encode failed"); exit(1) }
try! png.write(to: URL(fileURLWithPath: args[2]))
print("OK \(Int(src.extent.width))x\(Int(src.extent.height)) -> \(args[2])")
