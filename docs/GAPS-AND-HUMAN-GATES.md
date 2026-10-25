# Gaps and human gates — what an agent cannot own

The following cannot be automated, and a stack that claims otherwise is selling something
you do not want to buy.

Being honest about this is what makes the rest of the system trustworthy.

## Legal and certification gates — Not automatable (cannot be automated, by law or by physics)

| Item | Why |
|---|---|
| **Class approval / plan approval** | A surveyor signs. Published agentic work targets **Approval in Principle (AIP)** as the achievable external validation, not full class approval |
| **Statutory certification** (Load Line, Tonnage, Safety Construction/Equipment, IOPP, etc.) | Issued by or on behalf of the flag administration |
| **Approved stability booklet and loading computer** | Requires class/flag acceptance and a document-control process |
| **Signed speed–consumption warranty** | A commercial commitment; requires a named engineer and sea-trial evidence |
| **Model tests where contractually or regulatorily required** | Physical facility, ITTC procedures, human interpretation |
| **Professional liability** | Every jurisdiction puts a named person on the drawings |

## Technical gaps

1. **Detailed design and fabrication constraints.** The published state of the art explicitly lists these as
   remaining limits. Weld preparations, bracket topology, block-assembly sequences, distortion control,
   residual stress and yard-specific standards are not yet solvable from rules alone.
2. **Vendor-specific equipment data.** Engine envelopes, pump curves, hatch cover ratings, HVAC units, switchgear
   — the agent must be *given* datasheets. It should request them, never assume them.
3. **Yard capability data.** Crane capacity, dock/berth dimensions, panel-line limits, standard section
   inventory, weld procedures. Constructability scoring is only as good as this data.
4. **Cost data.** Steel prices, labour rates by zone, equipment quotes, yard overhead. Without a calibrated
   cost model, cost scores are fiction.
5. **Novel configurations.** No parent ship → empirical methods are out of their validity band → CFD needs
   validation → model tests are needed. The agent must recognise this and escalate rather than produce a
   confident wrong answer.
6. **Rule text is not machine-readable.** Class rules are published as prose/PDF. Building the clause database
   (and keeping it current with rule-change notices) is a real engineering project in itself, and it is the
   highest-leverage one in this whole stack.
7. **Legacy and tacit knowledge.** Parent-ship data, yard know-how, owner operating experience, and the "we
   tried that in 2011 and it cracked" knowledge live in people and file shares.

## Production and physical build (a separate automation problem)

Even a perfect design agent does not build a ship. Physical shipbuilding automation exists but is industrial
robotics and yard IT, not LLM agents:

- automated panel lines, plate cutting and marking (NC from nesting software)
- robotic welding for sub-assembly and block assembly, one-side welding processes
- CNC bending and profile processing
- block transport, erection and docking sequencing
- laser metrology and automated inspection/quality control
- sea trials, commissioning and crew training

The trend in the industry is a **single integrated platform** rather than an agent per tool: HD Korea
Shipbuilding & Offshore Engineering and Siemens Digital Industries Software signed an agreement (July 2026) to
build a next-generation marine platform connecting initial design and engineering through production,
logistics, quality inspection, sea trials and lifecycle management in one 3D data environment, where design
changes propagate instantly to the shop floor and shop-floor/supplier updates feed back into decisions.
HD Hyundai is separately working with ABS and Siemens on digital-twin technology for safety assessment of
ammonia-fuelled ships. An LLM agent stack is best positioned as the *reasoning and orchestration layer* on top
of that kind of environment — not as a replacement for it.

## Where humans should be, by stage

| Stage | Human role |
|---|---|
| Brief | Owner + designer define and freeze; agent drafts the requirement matrix |
| Concept / sizing | Naval architect reviews trade studies and picks the concept family; agent generates and scores |
| Preliminary design | Agent runs the discipline solvers and iteration; engineer reviews gates and exceptions |
| Class submission | Agent assembles the package; **engineer of record signs** |
| Contract design | Joint: agent produces, humans negotiate with owner and vendors |
| Production design | Yard engineers own standards; agent handles extraction, checking and documentation |
| Build | Yard production management; agents support planning, QC data and rework analysis |

## Recommended first project (highest chance of a real result)

Pick a **conventional ship type with good parent data** and a **mature rule set**:

- a bulk carrier or product tanker cargo-hold/midship structural optimisation with CSR rule gates, or
- a workboat / crew transfer vessel / ferry concept with intact + damage stability and powering, or
- a floating structure where an AIP-style automated reviewer gate has already been demonstrated.

Scope it as *brief in → class-submittable preliminary design package out*, with the automated reviewer gate and
human sign-off. Instrument everything, log every run, and make the whole package reproducible from a single
command. That reproducible audit trail is what convinces a class society and an owner to trust the rest.
