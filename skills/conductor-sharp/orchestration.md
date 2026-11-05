# Multi-Phase Order Orchestration

Part of the ConductorSharp skill ([SKILL.md](SKILL.md)).

Applies to apps that implement TM Forum style order orchestration on Conductor: a **service layer** receives service orders (TMF641) and creates resource orders (TMF652); a **resource layer** executes each resource order against southbound systems and records the result in resource inventory (TMF639). Many apps contain both layers, as one host or as two hosts sharing a common project. Skip this file for plain Conductor workflows.

The names of the context keys the platform passes to a phase workflow (`item`, `service_id`, `prepare_output`, ...) are defined by the orchestration platform that starts the phase workflows. The examples use the common ones; check the platform documentation for the exact names.

### Operations and phases

Each layer implements the operations **Add / Modify / Delete** per specification. Every operation consists of three workflows, called phases, that the platform runs in this order:

| Phase | Purpose | Side effects |
|---|---|---|
| **Preparation** | Collect everything the later phases need: extract characteristics from the order item, validate them, enrich them (catalog defaults, inventory lookups, current service snapshot). Output is typed data. | None on the systems being changed |
| **Feasibility** | Pre-flight checks that the change can be made (referenced service exists, not terminated, capacity available) | None on the systems being changed (a session or lock it opens is undone by its rollback) |
| **Fulfillment** | Do the work: trigger resource orders, call southbound systems, write results to inventory | Yes |

- All three phases always exist for every operation. A phase without work contains a single no-op worker: Conductor rejects a workflow definition without tasks
- A failure in preparation or feasibility rejects the order before anything was changed. Put every check that can fail cheaply there, before fulfillment starts changing systems
- Phase workflows are named by convention, with the names held in constants: `<layer>_<operation>_<kind>_<phase>` (for example `mailbox_add_resource_preparation`)

### Orders, items and ids

Two TM Forum order types drive the phases. Which one a workflow receives depends on its layer:

| | Service layer | Resource layer |
|---|---|---|
| Order | TMF641 service order (`ServiceOrder`) | TMF652 resource order (`ResourceOrder`) |
| Order item | `ServiceOrderItem`, its target in `item.service` | `ResourceOrderItem`, its target in `item.resource` |
| Target id | **service id**: the record in service inventory | **resource id**: the record in resource inventory |
| Operation | `OrderItemActionType`: Add, Modify, Delete | the same |

What a phase workflow can bind from its input (see *Data flow between phases* for the binding mechanics; the platform defines the exact keys):

| Value | Input key | Typical property | Layer |
|---|---|---|---|
| Order id | `order_id` | `OrderId` | service |
| Order item id | `item_id` | `ItemId` | service |
| Service id | `service_id` | `ServiceId` | service |
| The item's service | `item.service` | `Service` (nullable) | service |
| The whole order item | `item` | `Item` (`ResourceOrderItem`) | resource |
| Resource id | `resource_id` | `ResourceId` | resource |

```csharp
public class MailboxAddPreparationInput : WorkflowInput<MailboxAddPreparationOutput>
{
    public required string OrderId { get; set; }        // order_id (PascalCase converts to snake_case)
    public required string ServiceId { get; set; }      // service_id

    [JsonPropertyName("item.service")]
    public Service? Service { get; set; }               // the item's service; type from the TMF client package
}
```

- **Distinguish the ids.** The order id and the item id identify things inside one order: the item id is unique only within its order. The service id and resource id identify inventory records that outlive the order. A service layer that creates a resource order gets back a *resource order id*; the resource workflow it starts receives the *resource id*. Never pass one where the other is expected
- **The service id already exists on Add.** The platform creates the inventory record before preparation, which is why a preparation rollback deletes it
- **Prefer what the input already carries.** `item.service` or `item.resource` holds the requested characteristics, so extraction needs no API call. Handle it being null (return an empty result or throw a clear error) instead of dereferencing it
- **Fetch the whole order only when you need more than the item**: `GetServiceOrderAsync(orderId)` / `GetResourceOrderAsync(orderId)` on the TMF ordering client. Pick the item by its target id (`item.Service?.Id == serviceId`), never by index. Decide on multi-item orders explicitly: either reject them in validation or select by target id
- **Two sources of characteristics.** The order item says what is *requested*; inventory says what *exists*. Add reads the item. Modify and Delete read both: inventory for the current state (`GetServiceAsync(serviceId)`, then the specification from the catalog via `service.ServiceSpecification.Id`), the item for the change
- **Read characteristics through the specification, not by name.** `resource.ToEntityProxy<TProxy>(specification)` or a generic extraction worker (`ExtractServiceCharacteristics<TDto>`: inventory service, its catalog specification, mapped to a typed DTO) gives typed access and fails fast on a mismatching specification. The result becomes the typed preparation output (see *Data flow between phases*)
- **The operation** comes from the item's `Action`. Phases are separate workflows per operation, so a phase rarely branches on it; shared validators take it as a parameter (`Operation = OrderItemActionType.Add`)
- **Correlation:** when a phase creates a child order, set a deterministic `ExternalId` (for example the item id), so a retry finds the existing order instead of creating a second one

### Data flow between phases

A phase workflow does not receive the order directly. Its **workflow input** is assembled by the platform from:

1. **Context keys** (typical): the order id, the service or resource id, the whole order item (`item`, with `item.service` or `item.resource`), and for resource workflows the id of the resource instance (`ResourceId`)
2. **Outputs of earlier phases**, nested under one key per phase, for example `prepare_output`

Bind the input with `[JsonPropertyName]`. ConductorSharp uses the name verbatim in the generated expression, so a dotted name is a path into the workflow input:

```csharp
public class MailboxAddFulfillmentInput : WorkflowInput<MailboxAddFulfillmentOutput>
{
    [JsonPropertyName("service_id")]                              // context key
    public required string ServiceId { get; set; }

    [JsonPropertyName("prepare_output.order_data.domain_name")]   // <phase key>.<output property>.<field>
    public required string DomainName { get; set; }
}
// wf.WorkflowInput.DomainName  ->  ${workflow.input.prepare_output.order_data.domain_name}
```

Rules that keep the flow maintainable:
- **Extract once, in preparation.** Parse the order item a single time and emit it as one typed object (`OrderData`, `ResourceData`, `ServiceData`, `EnrichedAttributes`). Later phases bind to those fields and never re-parse the order item
- Preparation output property names become snake_case path segments (`OrderData` becomes `order_data`), so the output type is a contract: renaming a property breaks the later phases' bindings. Cover it with a test
- Feasibility and fulfillment can read the outputs of the phases before them, including the **feasibility output** in fulfillment: it arrives under `feasibility_output`, next to `prepare_output`. A feasibility workflow whose output is empty only validates (it fails by throwing); give it output properties when fulfillment needs something it discovered (for example a looked-up device family)
- Besides dotted per-field bindings, a whole phase output can be bound as one typed property: `public required PrepareOutputType PrepareOutput { get; set; }` becomes `prepare_output`, and tasks then read `wf.WorkflowInput.PrepareOutput.Field`. Prefer this when many fields are used; use dotted bindings for one or two
- `required` for mandatory fields, nullable for optional ones
- Add/Modify operations with identical inputs share an abstract input base class (`FulfillmentInput<TOutput> : WorkflowInput<TOutput>`)
- Reuse the worker's `Response` type as the workflow output property (`ResourceData = wf.ValidateInput.Output`) instead of copying fields

### Registering the phases with the platform

The platform decides which workflows to run for an order from a **mapping**: (specification id, action) to (preparation, feasibility, fulfillment workflow names). Register it at startup, idempotently (upsert), after the specifications themselves were imported:

```csharp
// Illustrative: the mapping client API belongs to your order platform
await mappingClient.UpsertAsync(new WorkflowMapping(
    SpecificationId: MailboxService.Id,
    Action: ServiceAction.Add,
    Preparation: Constants.Workflows.MailboxAdd.Preparation,
    Feasibility: Constants.Workflows.MailboxAdd.Feasibility,
    Fulfillment: Constants.Workflows.MailboxAdd.Fulfillment), cancellationToken);
```

- One `BackgroundService` does: import specifications, then register all mappings. Do not swallow its failure with a log line (the host would run unmapped): retry with backoff or fail startup
- Adding a workflow means adding its mapping; add a test that every workflow class is mapped and every mapping points at an existing workflow

### Service layer: creating resource orders

A service-layer fulfillment turns the service order into one or more resource orders and follows each through to completion:

```
TriggerOrderA -> wait for completion -> post-check -> read attributes A
  -> TriggerOrderB (uses attributes of A) -> wait -> post-check -> read attributes B
  -> persist output attributes on the service
```

- Resource orders run **serially** when one needs output of another (an id created by A is an input of B); keep that dependency explicit by feeding `wf.ReadAttributesA.Output.X` into the next trigger request
- Each trigger worker only creates the order and returns **the order id**. No polling, no inventory reads, no waiting in the worker
- A trigger builds the resource order from the catalog specification:

```csharp
var specification = await catalogClient.GetResourceSpecificationAsync(MailboxResource.Id, cancellationToken);

var resource = new ResourceRefOrValue
{
    Type = "LogicalResource",
    Name = $"Mailbox-{request.DomainName}",
    ResourceSpecification = new ResourceSpecificationRef { Id = MailboxResource.Id, Name = MailboxResource.Name }
};
var proxy = resource.ToEntityProxy<MailboxEntityProxy>(specification);   // typed access to characteristics
proxy.DomainName = request.DomainName;
proxy.QuotaMb = defaults.QuotaMb;            // configured defaults come from options, not literals
proxy.MailboxId = 0;                          // output characteristic: placeholder, the resource workflow overwrites it

var order = await orderingClient.CreateResourceOrderAsync(new ResourceOrder_Create
{
    State = ResourceOrderStateType.Acknowledged,
    Description = $"Mailbox create for {request.DomainName}",
    OrderItem =
    [
        new ResourceOrderItem
        {
            Id = "1", Quantity = 1,
            Action = OrderItemActionType.Add,
            State = ResourceOrderItemStateType.Initial,
            Resource = resource,
            ResourceSpecification = new ResourceSpecificationRef { Id = MailboxResource.Id, Name = MailboxResource.Name }
        }
    ]
}, cancellationToken);

return new Response { OrderId = order.Id ?? throw new InvalidOperationException("Resource order was created without an id.") };
```

  - Set **all mandatory characteristics** at creation: order acceptance usually validates them. Output characteristics that the resource workflow computes later get a non-empty placeholder
  - Characteristic access goes through typed proxies generated from the catalog specification when the project has them (assigning a proxy property writes into the entity's characteristic list). Without generated proxies, put characteristic access behind one helper class; never scatter characteristic name literals
  - Defaults the service layer owns (credit limits, quotas, classes) are applied here, so the resource layer can read them from the order (see *Resource layer*)
- **Modify** orders reference the existing resource: load it from inventory, build the order resource with its `Id`, `Href`, `Type`, `Name`, status and specification, copy the existing characteristics, then apply the changes. Action `Modify`
- **Delete** orders also carry the target's complete characteristic set, copied from inventory including each characteristic's `ValueType` (a platform that writes order characteristics back onto the inventory record would otherwise erase them). Implement it once as an abstract generic handler (`TriggerDeleteOrderHandler<TRequest, TProxy>`) with abstract members for specification id, order description and log text, and a virtual validation hook that calls `ToEntityProxy` so a mismatching resource fails fast
- Find the resource a service refers to in preparation (supporting resources of the service instance) and carry its id in the preparation output; fulfillment then triggers the order for exactly that id

**Reading results.** After completion, read output attributes from **resource inventory** by resource id; the resource workflow writes them there, the order itself does not carry them. Characteristic values can come back as strings: parse numbers with `CultureInfo.InvariantCulture`.

**Persisting on the service.** The last fulfillment step merge-patches the service instance (output attributes, name, supporting-resource links). Supporting-resource references copy `Href` and `@type` from the inventory resource instead of synthesising them.

**Snapshot enrichment for Modify and Delete.** If the platform applies the order's service value as a merge-patch on the service inventory, every field missing from the order is erased (name, state, supporting resources, characteristics not on the order). A preparation worker therefore reads the current service from inventory and writes the missing fields into the order item: on Modify only what the order does not already carry, on Delete everything.

### Waiting for resource order completion

Do **not** poll inside a worker: it blocks a worker slot and ties up a Conductor task for the whole duration. Choose one of these designs.

**1. Event-driven wait (preferred).** The ordering service notifies a listener when an order changes state (TMF652 `ResourceOrderStateChangeEvent`); the listener signals the waiting workflow through the `SignalWait` pattern of `ConductorSharp.Patterns`:

```csharp
// Startup
.AddSignalWait<PersistentSignalStore>("my_app")      // ISignalStore implementation backed by a database

// Workflow
public required SignalWait WaitForOrder { get; set; }
public required OrderPostCheck.Handler OrderPostCheck { get; set; }

_builder.AddTask(
    wf => wf.WaitForOrder,
    wf => new SignalWaitInput { SignalKey = $"resource_order:{wf.TriggerMailboxOrder.Output.OrderId}" }
).AsOptional();

_builder.AddTask(wf => wf.OrderPostCheck, wf => new OrderPostCheck.Request { OrderId = wf.TriggerMailboxOrder.Output.OrderId });

// Notification endpoint (outside the workflow): on a terminal state
await signalService.SendSignalAsync($"resource_order:{orderId}", TaskResultStatus.COMPLETED, outputData: null, ct);
```

- Requirements: the listener must be registered with the ordering service (at startup); the signal key is derived from the order id on both sides (constant prefix); use a **persistent** `ISignalStore` in anything but development (`InMemorySignalStore` loses signals on restart and does not work with several replicas)
- A signal that arrives before the workflow reaches the wait is kept in the store and picked up by the `RegisterWaiter` step or the `SignalSweeperService`; an order that finished while the app was down needs a reconciliation step at startup that re-sends signals for orders already in a terminal state
- `SignalWaitOutput` is empty: the signal carries no data to the workflow. Read the results from the system of record after the wait
- **The signal sender and the waiting workflow must use the same Conductor server and signal store.** If the layers run against separate Conductor instances, the signal never reaches the waiting task and the workflow hangs. Verify the topology before writing fulfillment code; otherwise use design 2 or 3
- If your organisation ships a shared package or sub-workflow that wraps listener, store and wait, use it instead of re-implementing it

**Optional wait plus post-check.** Make the wait `.AsOptional()` and follow it with a post-check worker that **GETs the order** and decides from its state. This keeps the root cause visible: the order's own error message is what fails the service-layer task, instead of an anonymous wait failure.

```csharp
// Failed, Partial, Held, Cancelled and Rejected are not a successful provision
if (IsFailedState(order.State))
{
    var (code, reason) = FirstCodedError(order);                 // item-level errors first, then order-level
    throw new StructuredErrorException(code, reason ?? $"Resource order {orderId} failed.", referenceError: null, reason);
}
```

**2. Poll the order.** A `DoWhile` loop (or a sub-workflow that restarts itself) with `WaitSeconds` between `GET resourceOrder/{id}` calls until a terminal state. The order state is authoritative. Use a bounded number of attempts and fail with a clear error.

**3. Poll inventory.** Wait until the resource appears with the expected status. Infers completion instead of observing it, so use it only when the order cannot be read.

After any design: verify the resulting resource status (for a Delete the expected status is the terminal one, for example `Suspended`), then read attributes from inventory.

### Resource layer: executing one resource order

Per resource specification and operation, the three phases look like this:

| Phase | Typical work |
|---|---|
| Preparation | Validate and extract the characteristics of `item.resource` into `ResourceData`; read configured defaults the service layer put on the order into `EnrichedAttributes`; for Modify/Delete also validate against the current inventory record |
| Feasibility | No-op, or checks on the resource itself |
| Fulfillment | Southbound call(s), then record the result in inventory |

- **Input**: the platform-provided resource instance id (`ResourceId`) plus `prepare_output.resource_data.*` and `prepare_output.enriched_attributes.*`
- **Validate with rules, not scattered ifs**: one rules class declares per characteristic whether it is required and which pattern it must match; the validate worker applies it and throws a validation error
- **Southbound workers** wrap one client call each, translate the client's exceptions through the error mapper, and return only what later tasks need. Long-running southbound operations are awaited inside the client with a bounded, backoff-based poller, not in the workflow
- **Idempotency**: a re-run must not duplicate work. Check for the existing remote object first (get-or-create). When a remote id has to survive between orders, keep it on an inventory record keyed by something stable (a tenant or customer id) and read it back
- **Branching**: use a Switch task for create/update/recreate branches. After the branches, **re-read the authoritative value from one source** in a join step instead of reading it from whichever branch ran
- **Record the result** in a final worker (`PopulateAttributes`):
  1. GET the inventory resource first, so the merge-patch does not drop characteristics that are already there
  2. Keep `@type` (use `LogicalResource` when the GET returned none)
  3. Set input and output characteristics through the proxy
  4. Set the resource status (for example `Available`) and `MergePatch` the resource
  The service layer later reads the output characteristics from this record
- **Delete**: either a southbound delete followed by a worker that records the final attributes, or a no-op fulfillment when the platform transitions the resource status itself. Do not set a status the platform sets; copy the full characteristic set
- Idempotent re-create after delete: a southbound object that is deliberately kept stays referenced by its inventory record, so the next Create updates it instead of creating a duplicate

### Rollback phases

A phase that fails after changing something leaves that change behind. The platform can run an optional **rollback workflow** per phase (preparation, feasibility, fulfillment) when that phase fails; how a rollback is attached to a phase, and what input it receives, is defined by the platform, so check its documentation. A rollback undoes only what its own phase did:

| Rollback of | Typically undoes |
|---|---|
| Preparation | Entries it registered (for example a service inventory record) |
| Feasibility | Anything the checks opened and left open (a session, a lock) |
| Fulfillment | The changes it made on southbound systems |

- Bind the rollback input like any phase input: ids as context keys, earlier outputs as `prepare_output`. A value that may not exist yet (the failure can happen early) is nullable
- **Idempotent**: it can run on a half-finished phase or twice. Treat "already gone" as success
- **Decide from observed state, not from assumptions**: fetch what exists, then branch with a Switch task, instead of deleting blindly
- **Cleanup that must not hide the original failure** (releasing a lock, closing a session) is `.AsOptional()`
- Make the forward phase record what the rollback needs (ids of created objects) so the rollback does not have to rediscover it
- A rollback is not a retry: it must not repeat the call that just failed
- Keep rollbacks that are the same for every operation (delete the registered entry, terminate the session) in one shared set; add a custom one only for an operation with its own side effects

```csharp
public override void BuildDefinition()
{
    _builder.AddTask(wf => wf.FindMailbox, wf => new() { ServiceId = wf.WorkflowInput.ServiceId });

    _builder.AddTask(
        wf => wf.MailboxExists,
        wf => new SwitchTaskInput { SwitchCaseValue = wf.FindMailbox.Output.State },   // Present or Missing
        new DecisionCases<MailboxAddFulfillmentRollback>
        {
            [nameof(MailboxState.Present)] = sc => sc.AddTask(wf => wf.DeleteMailbox, wf => new() { ServiceId = wf.WorkflowInput.ServiceId }),
        }
    );

    _builder.AddTask(wf => wf.ReleaseLock, wf => new() { ServiceId = wf.WorkflowInput.ServiceId }).AsOptional();
}
```

Test rollback workers like any worker (see [testing.md](testing.md)), including a second run that finds nothing left to undo.

### Layout of an orchestration app

These layouts are for workflow orchestration apps: worker services that register ConductorSharp workflows and workers. Pick by how many deployable apps there are; the folder shape inside an app is the same in all three.

**Rules for every layout**
- Per family (a service or resource specification): `<Family>/<Operation>/Workflows/` and `Workers/`, plus `<Family>/Common/` for validation rules, shared workers and input base classes. One worker per file with nested `Request`, `Response` and `Handler`
- Workflow and worker names, error codes and other names are constants, in one place
- Generated code (specification classes, API clients, task scaffolds) lives in its own folder or project, is never edited by hand and is regenerated by a documented command
- A `Wiremocks` project with WireMock mappings stands in for external systems, for local runs and tests
- Tests mirror the production folders; `Unit/` and `Integration/` are separate, so unit tests run without Docker

**A. One app, both layers** (default for a new app)

```
src/
  <Product>.Application/        # the one host: Program.cs, Dockerfile, appsettings
    <ServiceFamily>/            # service layer
    <ResourceFamily>/           # resource layer
    Common/  Mappings/
  <Product>.Commons/            # constants, options, shared hosting extensions
  <Product>.Domain/             # generated specification classes
  <Product>.<External>Client/   # optional: standalone client for an external API, no dependency on the other projects
  Wiremocks/
test/
  <Product>.Application.Test/   # Unit/  Integration/  Support/
  <Product>.<External>Client.Tests/
```

**B. Two apps, one per layer.** Use it when the layers must deploy and scale separately.

```
src/
  <Product>.Som.Application/    # service layer host (Program.cs, Dockerfile)
  <Product>.Rom.Application/    # resource layer host, with its own Clients/, Resilience/
  <Product>.Commons/  <Product>.Domain/    # shared by both
  Wiremocks/
test/
  <Product>.Application.Test/   # Unit/ and Integration/, each mirroring both hosts
```

**C. Platform host with many families.** What an app grows into; not a starting point.

```
src/
  <Platform>.API/               # ASP.NET host: configuration, migrations, serves documentation
  <Platform>.Application/       # <Family>/<Operation>/{Workflows,Workers}, a <Family>WorkflowMappings class per family,
                                # Common/Constants/<Family>/ for the names, Generated/ for task scaffolds
  <Platform>.Infrastructure/    # persistence, messaging, HTTP clients, hosted services
  <Platform>.<External>/        # one client library per external system
  <Platform>.Domain/            # specification classes
tools/                          # for example a generator for workflow documentation
tests/
  <Platform>.Application.UnitTests/    # mirrors Application, per family
```

- Constants: in A and B a `Commons` project (shared by hosts and tests); in C a `Common/Constants` folder inside `Application`, because there is one host
- Move from A to B only when the layers need separate deployment; split a client into its own project when something else could reuse it or it has to stay free of the rest of the app
