# SwiftPegasus.com

The 3D interactive website for <a href="https://swiftpegasus.com/"><samp>SwiftPegasus.com</samp></a>.

## Credit

This site is a fork of the wonderful 3D interactive portfolio created by **Henry Heffernan** ([henryheffernan.com](https://henryheffernan.com/), [original repo](https://github.com/henryjeff/portfolio-outer-site)). All credit for the design, 3D scene and code goes to him. See `LICENSE.md` for the original copyright notice.

<br>

To setup a dev environment:

```bash
# Clone the repository

# Install dependencies 
npm i

# Run the local dev server
npm run dev
```

To serve a production build:

```bash
# Install dependencies if not already done - 'npi i'

# Build for production
npm run build

# Serve the build using express
npm start
```

<br>

## Changing the text painted on the 3D model

The labels on the monitor, PC and keyboard, and the credits sheet on the wall, are painted into the model textures. To change them, edit `tools/textures.json` and run:

```bash
pip install pillow numpy
python3 tools/customize-textures.py
```

The script always starts from the untouched textures in `tools/original-textures/`, so you can re-run it as often as you like.
