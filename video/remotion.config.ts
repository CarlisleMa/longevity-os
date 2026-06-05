import { Config } from "@remotion/cli/config";

// High-quality H.264 output for a class submission video.
Config.setVideoImageFormat("jpeg");
Config.setPixelFormat("yuv420p");
Config.setCodec("h264");
Config.setCrf(18);
Config.setOverwriteOutput(true);
// Chrome headless shell renders the React DOM frame-by-frame.
Config.setChromiumOpenGlRenderer("angle");
