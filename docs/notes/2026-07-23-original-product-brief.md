# Original product brief (2026-07-23, gradius)

> Preserved verbatim from the founding planning session — this was the prompt that
> kicked off the project (originally lived in README.md). The distilled, current
> versions of everything here are ARCHITECTURE.md, PLAN.md, and DECISIONS.md; this
> file is the primary source.

# Project Plan
This is a fresh project. I'm thinking about building a modern version of Maltego (the node and transform based investigation tool), and I would like to walk through the implementation details and write down a detailed plan that I can start implementing with some additional agents. I would like you to walk through questions and details you think I should be asking, and be a codesigner with me. Here's what I'm thinking in terms of tech stack, please feel free to recommend other options:

# My personal experience
- Cybersecurity and Security Engineering
- Backend: familiar with python, go, rust
- Frontend: not very experienced here, so I'll lean on your prompting and direction, but I'm happy to have strong opinions
- Cloud: familiar with GCP(1st) and AWS (2nd)
- Other: Docker, kubernetes, virtualization, terraform, ansible

# Key Points
- I don't want to overengineer for production and scaling, but I want to keep it in the back of our minds at all times
- We don't need to be ready to deploy to Cloud on day 1, but I want to have a path for getting there, whether that's just rolling docker containers in a VM provider (DigitalOcean, Hetzner), or managed containers in GCP/AWS
- I'm thinking we go the direction of one stack per tenant instead of multi-tenency, as this is a security-centric product, so this makes sense to me, and its easier to manage
- Grid is a working title, the product name is still undecided

# Rough Tech Stack
- Modern React stack frontend
- Modern Typed Python backend using FastAPI
- Efficient datastore - DuckDB, Postgres, etc: I'm less sure about what makes the most sense here, so I'll talk you through some of my goals and we can figure it out. Definitely want something performant, but also easy to deploy regardless of destination
- Modern dev tooling for the Python stack: ruff for linting, uv for package management, ty for python type checking
- Probably an ORM for the database backend, though I could be convinced to just use some form of raw SQL if you think it's best
- Thinking something like Temporal for durable task management
- Modern dev tooling for the frontend including pnpm, and whatever other tooling you would recommend
- Extensive test suite for front and backend, intentional test-based designs so that we can ensure everything works
- Makefiles for both frontend and backend, repeated tasks and management should be included in this
- Docker for easy infrastructure management both in development and release

# Core Product Ideas
- Each case is an infinitely expandable graph frontend, where you can create notes that represent different data types (domains, IPs, emails, plaintext, other custom data types, or whatever we might choose)
- Strong LLM integration, LLMs and AI are first class collaborators on this product and are front and center features
  - LLMs will have direction on how to interact with the graph and data on the graph, can be asked questions about the data and our API backend makes it easy for the LLMs to discover the data that's required to answer questions and produce work
  - Support for frontier models and providers (eg: Anthropic, OpenAI) but also support for model proxies like OpenRouter, as well as support for local LLMs
  - First class integration with multiple LLM models, being able to use multiple models and providers based on the goal: eg some models are better at particular tasks. User may also want to use local models for privacy-centric or cyberdefense work
  - LLMs are also able to interact with the graph and help develop integrations and transforms, it should be easy to summon a development chat like claude code, we want the LLMs to be presented as pretty much coworkers
- Operating the product is a collaboration effort, multiple people can be working on the graph at the same time
- Nodes can be connected via particular data types, whether they're relationships (eg: IP -> Domain) or context related (eg: plaintext note saying that this email address was found on this web page)
  - The connections will not only provide context for investigators, but can have automation related to them, eg, if a node has an email associated, with it, we can search that webpage's domain registrar for other pages owned by that email
  - The connections provide context for the LLMs that are interacting with the graphs
- Nodes can be grouped together in regions or folders, or whatever we want to call them, that can have additional context - eg: all nodes can be related to a single actor group and we can have automation that operates on actor groups
- You can save locations on the graph to quickly navigate between large collections of data, and highlight spots for your collaborators
- Nodes can be operated on by transforms - eg: turning IPs to Domains, looking up email addresses, etc.
- Transforms should exist for all supported data types, but it should be very easy to plug in and create new transforms
  - I'm thinking the transform model will be based on Python plugin files, or even more simply, a standard REST API configuration. The REST API should provide a discoverable endpoint that will allow us to autoconfigure it in our product
  - We should also make it easy to plug our product into existing APIs and even target first party support for some things like VirusTotal, Shodan, etc
- When enabled, graphs can share information between each other, essentially acting as a sort of Threat Intel Platform, sharing data as a central codex, populating information between graphs and projects, when this is desired, but can be isolated
- Providing discovery tools when graphs share information and are configured to collaborate, want to make sure we have context awareness as we're doing investigations and such
- Interaction with the product via API is a first-class citizen. Users should be able to automate anything that we're allowed to do on the platform.
- Multi-user, single tenant. Simple auth for now, but plan to support other auth like OAuth, SSO, SCIM, etc - build the authentication with strong authz/authn in mind
- UI is clean, and designed to be easily themed. I would like to start with an industrial style theme, with monospace font, following design language from places like usgraphics.com, clean sharp lines
  - The goal is to start the design with the ability to easily tweak the look and feel if needed, accessibility like light mode and dark mode, as well as readable fonts, etc, are important
- Sleek keyboard shortcut-based UX for users that want it, as well as the ability to navigate around via keyboard alone if wanted - for power users
- Users can bring their own LLM providers, or we can provide it for them, either bundled into the cost, or after a period, cost passed on to the user
- Focus on keeping collaboration, exploration, and ease of discovery front and center. Users should be able to embed documentation and easily guide their coworkers around, even if the team is fully remote.

Any other questions? Can you walk through the implementation plan for an MVP with me? Feel free to break it down into phases if that makes the most sense, in the order that makes the most sense. The goal is to pass this plan off to a smaller model that can implement steps one by one, and then request for clarifications from both myself and you (the more expensive, more experienced model), so call that out in their CLAUDE.md. Yes, lets also design the CLAUDE.md now so that this entire code base is designed with agentic development in mind. I want to make sure the agents are easily able to understand, discover, organize and implement the code base, and any time they need help they should know to reach out to us.

Also at any point in time if you have an idea or inspiration that you think would fit into the product, you're welcome to bring it up. This can be a creative endevor for you as well, and I appreciate and value your suggestions and feedback. Let's keep ample notes, lots of documentation for the entire development process. I dont want to lose anything that we do or think of. We can definitely also keep a running list of ideas and inspiration for the product.

Quick note, this is just planning time. I'm going to work on setting up our dev environment while you're planning all this out. Please do not implement any code yet.
