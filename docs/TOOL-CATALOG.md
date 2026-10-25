# Tool catalog — what an agent can actually drive

"Agent-drivable" = there is a documented programmatic interface (Python/CLI/script/MCP/API), not just a GUI.

## Agent infrastructure

| Tool | Interface | Use |
|---|---|---|
| Agent Skills (`SKILL.md` open standard) | filesystem skills, portable across Claude Code, Codex, Cursor, Gemini CLI and others | encode discipline knowledge, workflows and rule-checklists as reusable skills; large public marketplaces exist |
| MCP servers | Model Context Protocol | wrap any engineering tool as a callable tool |
| FreeCAD MCP | Python/MCP | parametric 3D CAD automation, including the Ship workbench |
| Blender MCP | MCP | geometry, visualisation, presentation models |
| OneWorkflow (DNV open source) | Python orchestration of Sesam command chains | run analysis workflows locally or in cloud, from an agent |
| `dnv-sesam-commands` (PyPI) | Python library | build and execute Sesam workflows programmatically |

## Naval architecture / hydrostatics / stability

| Tool | Interface | Notes |
|---|---|---|
| **`navaltoolbox`** (PyPI) | Python + Rust core, `pip install navaltoolbox` | Hydrostatics (∇, COB, Awp, LCF, BMt/BMl, free-surface), GZ curves with automatic trim optimisation, multi-hull support, downflooding detection, tank management and sounding tables, appendages, deck edges for freeboard, loading conditions, wind heeling from silhouette DXF, **Rhai scripting for custom stability criteria**, Plotly/Matplotlib output. AGPL-3.0. Ideal as the open deterministic backend |
| **Maxsurf** (Bentley) | Modeler/Stability/Resistance/Motions/Structure; **an MCP server exists** that lets an agent model the hull, define tanks and compartments and run intact + damage stability autonomously | Strongest commercial route to an agentic stability workflow today |
| **NAPA** (+ Designer/Engineer, 2026.x releases) | Manager application concept, batch/scriptable | Industry standard for design, stability, structural and performance |
| **GHS** | command/run files — fully scriptable | The classic loading-computer/stability engine; agent writes run files |
| **DNV Nauticus Stability** | class-supported tooling | stability and loading |
| **Vessel.js** (shiplab) | JS object-oriented library, open | Ship design object model + resistance (Holtrop) — good for a web/agent-native design kernel |
| **FreeCAD Ship workbench** | Python, open source | Displacement, centre of buoyancy, transverse stability, hydrostatics plots, seakeeping helpers |
| Orca3D (Hull Assistant, Planar, SeaPower) | documented automation API | hull definition → hydrostatics → resistance/powering |
| DELFTship / FreeShip++ | file-based hull formats | open hull modelling and hydrostatics |
| MOSES / AQWA / WAMIT / HydroD / ShipMo3D | scripting / file input | hydrostatics and motions for offshore floaters and seakeeping |

## Hull form generation and optimisation

| Tool | Interface | Notes |
|---|---|---|
| **CAESES / FRIENDSHIP** | fully parametric + morphing, commandable, surrogate modelling, DoE and optimisation | the standard for agent-driven hull design-space exploration |
| Rhino + Grasshopper / Rhino.Inside / rhino3dm / rhino3dm.py | Python + RhinoCommon | mature automation path, huge ecosystem |
| `geomdl`, `pythonocc`, Open CASCADE | Python | NURBS hull surfaces without a licence |
| ShipGen / ShipD (MIT Decode) | research: 30,000 parametric hull designs + performance metrics and meshes | dataset for learned hull generation and surrogate models |
| Published parametric-variant methods (e.g. frigate-hull variant generators) | open code | generate families of hull variants from a parent |

## Resistance, CFD, propulsion

| Tool | Interface | Notes |
|---|---|---|
| OpenFOAM (`interIsoFoam`, overset, DTC/shipFoam variants) | CLI + case dictionaries — trivially agent-driven | free-surface RANS; needs documented grid convergence |
| STAR-CCM+ / ANSYS Fluent / Fine(Marine) | Java/Python macros, recorded and replayable | commercial ship CFD |
| Holtrop–Mennen, Hollenbach, Savitsky, ITTC-57 | implement in Python | empirical powering; state applicability bands |
| OpenProp (MIT) | Python/MATLAB | preliminary propeller design, B-series style maps |
| Model test data (MARIN, HSVA, SVA, NMRI) | benchmark hulls KCS, KVLCC2, DTMB 5415 | for validating the agent's CFD pipeline |

## Structure and FE

| Tool | Interface | Notes |
|---|---|---|
| **DNV Sesam** (GeniE, HydroD, Sestra, Usfos, Submod) | `dnv-sesam-commands` Python library, Sesam Manager batch, command files, code-check runs | the cleanest commercial agent-drivable FE chain in marine |
| **DNV Nauticus Hull** | DNV ship rules + CSR BC & OT rule checks with compliance documentation | scantlings and rule evidence |
| **ABS engineering software** (e.g. PolarQuickCheck) | IACS UR-based local scantling checks | quick rule verification |
| CalculiX | CLI, `.inp` files | used as the deterministic solver backend in published agentic topology-optimisation work (BESO) |
| Code_Aster, Elmer, PrePoMax | CLI / Python | open FE alternatives |
| `gmsh`, netgen | Python API | meshing with convergence studies |
| IACS CSR rule engines / class rule PDFs | needs your own machine-readable encoding | encode clause → formula → limit as data |

## 3D production design, PLM and yard systems

| Tool | Interface | Notes |
|---|---|---|
| CADMATIC (Hull, Outfitting, eShare, Information Management) | APIs, data-driven model | production design and drawing generation |
| AVEVA Marine / Everything3D / AVEVA NET (PLM) | .NET APIs, Integration Service | 3D model, drawings, PLM data flow |
| FORAN (Siemens) | integrated design & production | part of the Siemens marine stack |
| Siemens NX / Solid Edge / Teamcenter | APIs, JT data | the HD KSOE + Siemens integrated platform targets one 3D data environment across design → production → logistics → quality → sea trials → lifecycle |
| SigmaNEST / Lantek / ESAB nesting | import DXF/STEP, NC output | plate nesting, bevel and NC code generation |
| Shipyard ERP (SAP, Oracle, or yard-specific) | APIs | procurement, work packages, schedule, cost |

## Regulatory, class and data platforms

| Resource | Access |
|---|---|
| IMO instruments: SOLAS, MARPOL, Load Line, Tonnage, Polar Code, IGC/IGF, HSC Code, IS Code, Fire Safety Systems Code, FTP Code, ISO 15016, ITTC procedures | publications; encode the applicable clauses as data |
| IACS URs and CSR | published; machine-encode for rule gates |
| DNV Veracity | data/marketplace platform, digital services |
| ABS, LR, BV, CCS, RINA, NK, ClassNK digital channels | plan submission, AIP workflow, rules online |

## Documents, drawings and reporting

| Tool | Interface |
|---|---|
| `ezdxf` | Python DXF generation — lines plans, GA line work, details |
| `matplotlib` / `plotly` | hydrostatic, GZ, RAO, power curves |
| Typst / LaTeX | stability booklets, calculation reports, reproducible PDF |
| `python-docx`, `openpyxl`, `python-pptx` | owner-facing spec, weight/cost tables, review decks |
| MarkItDown / Docling / pdfplumber | ingest owner requirements, class circulars, vendor datasheets into `brief.json` |
| SQLite / DuckDB | rule database, requirement traceability, run registry |
