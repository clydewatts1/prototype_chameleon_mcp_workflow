# 📚 Chameleon Documentation Index

Complete reference documentation for the Chameleon MCP Workflow Engine.

## 🏛️ Architecture & Design

**CORE - DO NOT CHANGE**:
- [**Workflow_Constitution.md**](architecture/Workflow_Constitution.md) - Constitutional design document. The source of truth for all architecture decisions. **Protected document.**

**Design Specifications**:
- [Database_Schema_Specification.md](architecture/Database_Schema_Specification.md) - Complete Tier 1/Tier 2 schema with all tables, columns, and relationships
- [UOW Lifecycle Specifications.md](architecture/UOW_Lifecycle_Specifications.md) - Unit of Work state machine and lifecycle rules
- [Role_Behavior_Specs.md](architecture/Role_Behavior_Specs.md) - ALPHA, BETA, OMEGA, EPSILON, TAU role behaviors and responsibilities
- [Guard Behavior Specifications.md](architecture/Guard_Behavior_Specifications.md) - PASS_THRU, CRITERIA_GATE, DIRECTIONAL_FILTER, CONDITIONAL_INJECTOR guard logic
- [Interaction & Topology Specifications.md](architecture/Interaction%20&%20Topology%20Specifications.md) - Component connections and workflow topology

**Features**:
- [Dynamic_Context_Injection_Specs.md](architecture/Dynamic_Context_Injection_Specs.md) - DCI feature, model override, instruction injection, knowledge fragments
- [Memory & Learning Specs.md](architecture/Memory%20&%20Learning%20Specs.md) - Role attributes, global blueprints vs personal playbooks
- [Workflow_Import_Requirements.md](architecture/Workflow_Import_Requirements.md) - YAML structure and import semantics

## 🎓 User Guides

- [user_guide.md](user_guide.md) - End-user documentation for workflow creation and management
- [Testing Strategy & QA Specs.md](Testing%20Strategy%20&%20QA%20Specs.md) - QA methodology and testing approach

## 🔧 Implementation Details

- [BACKGROUND_SERVICES_IMPLEMENTATION.md](BACKGROUND_SERVICES_IMPLEMENTATION.md) - Zombie sweeper (TAU), heartbeat protocol, background task architecture
- [SEMANTIC_GUARD_IMPLEMENTATION.md](SEMANTIC_GUARD_IMPLEMENTATION.md) - SemanticGuard class implementation, condition evaluation, mutation payload handling
- [PERSISTENCE_SERVICE_API.md](PERSISTENCE_SERVICE_API.md) - InterventionStore interface and SQLAlchemy implementation
- [COMPONENT_REFACTORING_GUIDE.md](COMPONENT_REFACTORING_GUIDE.md) - Component refactoring methodology and patterns
- [COMPLIANCE_CHECKLIST.md](COMPLIANCE_CHECKLIST.md) - Constitutional compliance verification checklist

## 📖 Module-Level Documentation

Each module has its own README:

- [chameleon_workflow_engine/SERVER_PROMPT.md](../chameleon_workflow_engine/SERVER_PROMPT.md) - FastAPI server development guide
- [database/README.md](../database/README.md) - Database architecture and usage
- [common/README.md](../common/README.md) - Configuration management
- [tools/README_WORKFLOW_MONITOR.md](../tools/README_WORKFLOW_MONITOR.md) - Workflow monitoring tools

## 🎯 Quick Navigation

**For Architecture Questions**:
1. Start with [Workflow_Constitution.md](architecture/Workflow_Constitution.md)
2. Reference [Database_Schema_Specification.md](architecture/Database_Schema_Specification.md)
3. Check specific role/guard specs as needed

**For Feature Implementation**:
1. Review [Dynamic_Context_Injection_Specs.md](architecture/Dynamic_Context_Injection_Specs.md) for DCI
2. Check [UOW Lifecycle Specifications.md](architecture/UOW_Lifecycle_Specifications.md) for workflow flow
3. Reference module README for implementation details

**For Testing**:
1. Review [Testing Strategy & QA Specs.md](Testing%20Strategy%20&%20QA%20Specs.md)
2. Check [COMPLIANCE_CHECKLIST.md](COMPLIANCE_CHECKLIST.md) for constitutional compliance

**For Operations**:
1. Review [BACKGROUND_SERVICES_IMPLEMENTATION.md](BACKGROUND_SERVICES_IMPLEMENTATION.md)
2. Check [PERSISTENCE_SERVICE_API.md](PERSISTENCE_SERVICE_API.md)

## 📋 Documentation Status

✅ = Up-to-date | 🔄 = Under Review | ⚠️ = Needs Update

| Document | Status | Last Updated |
|----------|--------|--------------|
| Workflow_Constitution.md | ✅ | Phase 3 |
| Database_Schema_Specification.md | ✅ | Phase 3 |
| UOW Lifecycle Specifications.md | ✅ | Phase 3 |
| Role_Behavior_Specs.md | ✅ | Phase 3 |
| Guard_Behavior_Specifications.md | ✅ | Phase 3 (DCI added) |
| Dynamic_Context_Injection_Specs.md | ✅ | Phase 3 |
| BACKGROUND_SERVICES_IMPLEMENTATION.md | ✅ | Phase 3 |
| SEMANTIC_GUARD_IMPLEMENTATION.md | ✅ | Phase 3 |
| Testing Strategy & QA Specs.md | ✅ | Phase 3 |
| user_guide.md | 🔄 | Phase 2 |

## 🔐 Protected Documents

These documents define core constitutional design and should only be changed through formal architectural review:

- `architecture/Workflow_Constitution.md` - Only change for major architectural shifts

## 📝 Writing Guidelines

When adding documentation:

1. **Link to Constitution**: Reference Articles when relevant
2. **Use Specifications**: Refer to schema and behavior specs
3. **Include Examples**: Provide YAML examples where possible
4. **Keep Current**: Update docs when code changes
5. **Maintain Structure**: Follow the organization of this index

## 🤝 Contributing Documentation

1. Follow the structure in this index
2. Use clear headings and sections
3. Include code examples where helpful
4. Link to related documents
5. Update this index when adding new docs

---

**Last Updated**: January 2026  
**Version**: Phase 3.1 (DCI Complete)
