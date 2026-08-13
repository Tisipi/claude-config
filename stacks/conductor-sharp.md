# ABOUTME: ConductorSharp development guide - key concepts, patterns, and conventions for .NET Conductor workflow orchestration.

# ConductorSharp Development Guide

**Source**: https://github.com/codaxy/conductor-sharp
**Wiki**: https://github.com/codaxy/conductor-sharp/wiki

ConductorSharp is a .NET client library for Netflix Conductor providing a strongly-typed workflow builder DSL, task handlers, and quality-of-life additions.

## Installation

```bash
# Core
dotnet add package ConductorSharp.Client
dotnet add package ConductorSharp.Engine

# Optional
dotnet add package ConductorSharp.Patterns
dotnet add package ConductorSharp.KafkaCancellationNotifier
dotnet tool install --global ConductorSharp.Toolkit
```

## Core Packages

| Package | Purpose |
|---|---|
| `ConductorSharp.Client` | API communication with Conductor server |
| `ConductorSharp.Engine` | Workflow definition, task handlers, execution management |
| `ConductorSharp.Patterns` | Pre-built tasks (WaitSeconds, ReadWorkflowTasks, C# lambdas) |
| `ConductorSharp.Toolkit` | CLI for scaffolding definitions from existing Conductor server |
| `ConductorSharp.KafkaCancellationNotifier` | Event-driven task cancellation via Kafka |

## Core Concepts

### Workflows

Inherit from `Workflow<TWorkflow, TInput, TOutput>`. Input must extend `WorkflowInput<TOutput>`, output must extend `WorkflowOutput`. Inject `WorkflowDefinitionBuilder` via constructor.

Two equivalent conventions exist for workflow input/output — pick one and apply it consistently within a project:

**Option A — Nested `In`/`Out` classes (guide default):** input and output are inner classes of the workflow. Keeps everything self-contained, works well with `partial class`.

**Option B — Flat external classes:** input and output are separate top-level classes named `<WorkflowName>Input` / `<WorkflowName>Output`. More verbose but easier to reference from outside the workflow class. Access via `wf.Input` is identical in both options.

Use Option B unless the project already uses Option A — don't mix within a project.

```csharp
[OriginalName("domain_resource_preparation")]
[Version(1)]
[WorkflowMetadata(FailureWorkflow = typeof(FailAllRunningReports))]
public partial class ResourcePreparation(
    WorkflowDefinitionBuilder<ResourcePreparation, ResourcePreparation.In, ResourcePreparation.Out> builder
) : Workflow<ResourcePreparation, ResourcePreparation.In, ResourcePreparation.Out>(builder)
{
    public class In : WorkflowInput<Out>
    {
        public required string OrderId { get; set; }
        public required ResourceOrderItem Item { get; set; }
    }

    public class Out : WorkflowOutput
    {
        public required RpdDevice RpdDevice { get; init; }
        public required string Intent { get; set; }
    }

    // Task properties — become strongly-typed references in BuildDefinition
    public required GetDevicesFromInventory GetDevices { get; set; }
    public required SwitchTaskModel DecideAction { get; set; }
}
```

**Option B example (flat classes):**

```csharp
public class ResourcePreparationInput : WorkflowInput<ResourcePreparationOutput>
{
    public required string OrderId { get; set; }
}

public class ResourcePreparationOutput : WorkflowOutput
{
    public required string ResourceId { get; set; }
}

[OriginalName("domain_resource_preparation")]
public class ResourcePreparation(
    WorkflowDefinitionBuilder<ResourcePreparation, ResourcePreparationInput, ResourcePreparationOutput> builder
) : Workflow<ResourcePreparation, ResourcePreparationInput, ResourcePreparationOutput>(builder)
{
    public required GetDevicesFromInventory.Handler GetDevices { get; set; }

    public override void BuildDefinition()
    {
        _builder.AddTask(
            wf => wf.GetDevices,
            wf => new GetDevicesFromInventory.Request() { OrderId = wf.Input.OrderId }
        );
        _builder.SetOutput(wf => new ResourcePreparationOutput() { ResourceId = wf.GetDevices.Output.ResourceId });
    }
}
```

`BuildDefinition()` in the same or a partial file — always call `base.BuildDefinition()` first:

```csharp
public override void BuildDefinition()
{
    base.BuildDefinition();

    _builder.AddTask(
        wf => wf.GetDevices,
        wf => new GetDevicesFromInventory { OrderId = wf.Input.OrderId }
    );

    _builder.AddTask(
        wf => wf.DecideAction,
        wf => new SwitchTaskInput { SwitchCaseValue = wf.GetDevices.Output.Action },
        new DecisionCases<ResourcePreparation>
        {
            ["install"] = BuildInstallFlow,
            DefaultCase = BuildRemovalFlow,
        }
    );

    _builder.SetOutput(wf => new Out
    {
        RpdDevice = wf.GetDevices.Output.RpdDevice,
        Intent = wf.GetDevices.Output.Intent,
    });
}

// Delegate case builders to separate methods (preferred over inline lambdas for complex cases)
private static void BuildInstallFlow(ITaskSequenceBuilder<ResourcePreparation> sc) { /* ... */ }
private static void BuildRemovalFlow(ITaskSequenceBuilder<ResourcePreparation> sc) { /* ... */ }
```

### Task Handlers

Extend `TaskRequestHandler<TRequest, TResponse>` (abstract class, NOT an interface). Use primary constructor syntax for dependency injection. Use `sealed` where appropriate.

```csharp
public class GetDevicesFromInventory : IRequest<Response>
{
    public required string OrderId { get; set; }
}

public class Response
{
    public required RpdDevice RpdDevice { get; set; }
    public required string Intent { get; set; }
}

[OriginalName("domain_get_devices_from_inventory")]
public sealed class Handler(
    IServiceInventoryManagement4ApiClient serviceInventory,
    IResourceInventoryManagement4ApiClient resourceInventory
) : TaskRequestHandler<GetDevicesFromInventory, Response>
{
    public override async Task<Response> Handle(GetDevicesFromInventory request, CancellationToken cancellationToken)
    {
        var service = await serviceInventory.GetServiceAsync(request.OrderId, cancellationToken);
        return new Response { /* ... */ };
    }
}
```

- PascalCase properties auto-convert to `snake_case` in Conductor JSON
- Override with `[JsonProperty("custom_name")]` when needed
- Use `[Required]` on request model properties — validated by `AddValidation()` pipeline
- Use `required` keyword on all input/output properties

### Metadata Attributes

| Attribute | Target | Description |
|---|---|---|
| `[OriginalName("name")]` | Class | Custom task/workflow name in Conductor |
| `[WorkflowMetadata(...)]` | Workflow class | OwnerEmail, OwnerApp, Description, FailureWorkflow |
| `[Version(n)]` | Workflow class | Version number for sub-workflow references |
| `[TaskDomain("domain")]` | Task class | Assign task to specific domain |

Task metadata is configured at registration (not via attribute):
```csharp
services.RegisterWorkerTask<MyTaskHandler>(options =>
{
    options.OwnerEmail = "team@example.com";
    options.Description = "My task description";
});
```

### Expression Generation

C# property access and string interpolation auto-translates to Conductor expressions. Use `wf.Input` to reference workflow input (from inner `In` class):

```csharp
// C#
CustomerName = $"{wf.GetCustomer.Output.FirstName} {wf.GetCustomer.Output.LastName}"
Address = wf.Input.Address   // wf.Input references the workflow's In class

// Generated Conductor JSON
"customer_name": "${get_customer.output.first_name} ${get_customer.output.last_name}",
"address": "${workflow.input.address}"
```

**Supported expression features:**

- **Property chaining**: `wf.Task.Output.Field` — plain member access only; no method calls and no `Nullable<T>.Value` (see Known Limitations)
- **String interpolation**: `$"{wf.Task.Output.Name}"`
- **String concatenation**: `1 + "Str_" + wf.Input.Value`
- **Type casting**: `((FullName)wf.Task.Output.Name).FirstName` → `${task.output.name.first_name}`
- **Dictionary indexing**: `wf.Input.Dictionary["key"].Property` → `${workflow.input.dictionary['key'].property}`
- **Array initialization**: `new[] { 1, 2, 3 }` → `[1, 2, 3]`
- **Object initialization**: Nested objects and anonymous types supported
- **Workflow name embedding**: `NamingUtil.NameOf<MyWorkflow>()` → resolves `[OriginalName]` value

### Accessing Execution Context in Handlers

Inject `ConductorSharpExecutionContext` to access workflow/task metadata:

```csharp
public sealed class Handler(ConductorSharpExecutionContext context)
    : TaskRequestHandler<MyRequest, MyResponse>
{
    public override async Task<MyResponse> Handle(MyRequest request, CancellationToken cancellationToken)
    {
        var workflowId = context.WorkflowId;
        var taskId = context.TaskId;
        var correlationId = context.CorrelationId;
        return new MyResponse();
    }
}
```

## Task Types

### Simple Task

```csharp
_builder.AddTask(wf => wf.MyTask, wf => new MyTaskRequest { Input = wf.Input.Value });
```

### Sub-Workflow Task

Declare with `SubWorkflowTaskModel<TInput, TOutput>`:

```csharp
public SubWorkflowTaskModel<ChildWorkflowInput, ChildWorkflowOutput> ChildWorkflow { get; set; }

_builder.AddTask(wf => wf.ChildWorkflow, wf => new ChildWorkflowInput { OrderId = wf.Input.OrderId });
```

### Switch Task (Conditional Branching)

Declare with `SwitchTaskModel`. Use `DecisionCases<TWorkflow>` with builder lambdas or method references:

```csharp
public required SwitchTaskModel DecideAction { get; set; }

_builder.AddTask(
    wf => wf.DecideAction,
    wf => new SwitchTaskInput { SwitchCaseValue = wf.GetAction.Output.ActionType },
    new DecisionCases<MyWorkflow>
    {
        [nameof(ActionType.Install)] = sc => sc.AddTask(wf => wf.InstallTask, wf => new()),
        [nameof(ActionType.Remove)] = sc => sc.AddTask(wf => wf.RemoveTask, wf => new()),
        DefaultCase = BuildDefaultFlow,   // method reference preferred for complex cases
    }
);
```

### Dynamic Task

Task name resolved at runtime:

```csharp
public DynamicTaskModel<ExpectedInput, ExpectedOutput> DynamicHandler { get; set; }

_builder.AddTask(
    wf => wf.DynamicHandler,
    wf => new DynamicTaskInput<ExpectedInput, ExpectedOutput>
    {
        TaskInput = new ExpectedInput { OrderId = wf.Input.OrderId },
        TaskToExecute = wf.Input.TaskName
    }
);
```

### Dynamic Fork-Join

```csharp
public DynamicForkJoinTaskModel DynamicFork { get; set; }

_builder.AddTask(
    wf => wf.DynamicFork,
    wf => new DynamicForkJoinInput
    {
        DynamicTasks = wf.PrepareTasks.Output.DynamicTasks,
        DynamicTasksInput = wf.PrepareTasks.Output.DynamicTasksInput
    }
);
```

For dynamic fork-join with runtime-generated tasks, build `WorkflowTask` objects and serialize inputs as `JObject`:

```csharp
var tasks = new List<WorkflowTask>();
var taskInputs = new Dictionary<string, JObject>();

foreach (var item in items)
{
    var taskName = $"{workflowName}/{item.Id}";
    tasks.Add(new WorkflowTask
    {
        TaskReferenceName = taskName,
        Name = taskName,
        Type = "SUB_WORKFLOW",
        SubWorkflowParam = new() { Name = workflowName },
        Optional = true,
    });
    taskInputs.Add(taskName, JObject.FromObject(new { item.Id, item.Name }));
}
```

### Do-While Loop Task

Output is `NoOutput` — no strongly typed output available:

```csharp
public DoWhileTaskModel DoWhile { get; set; }

_builder.AddTask(
    wf => wf.DoWhile,
    wf => new DoWhileInput { Value = wf.Input.Loops },
    "$.do_while.iteration < $.value",  // Loop condition (JavaScript)
    builder =>
    {
        builder.AddTask(wf => wf.GetCustomer, wf => new GetCustomerRequest { CustomerId = "CUSTOMER-1" });
    }
);
```

### Lambda Task (JavaScript)

Output accessed via `Output.Result.Property` (not `Output.Property` directly):

```csharp
public LambdaTaskModel<LambdaInput, LambdaOutput> LambdaTask { get; set; }

_builder.AddTask(
    wf => wf.LambdaTask,
    wf => new LambdaInput { Value = wf.Input.Value },
    script: "return { something: $.Value.toUpperCase() }"
);

// Access output as: wf.LambdaTask.Output.Result.Something
```

### Wait Task

```csharp
public WaitTaskModel WaitTask { get; set; }

_builder.AddTask(
    wf => wf.WaitTask,
    wf => new WaitTaskInput { Duration = "1h" }  // or Until = "2024-01-01T00:00:00Z"
);
```

### Terminate Task

Use `TerminationStatus` enum, not string literals:

```csharp
public TerminateTaskModel Terminate { get; set; }

_builder.AddTask(
    wf => wf.Terminate,
    wf => new TerminateTaskInput
    {
        TerminationStatus = TerminationStatus.Completed,
        WorkflowOutput = new Out
        {
            RpdDevice = wf.GetDevices.Output.RpdDevice,
            Intent = wf.GetDevices.Output.Intent,
        }
    }
);
```

### Human Task

```csharp
public HumanTaskModel<HumanTaskOutput> HumanTask { get; set; }

_builder.AddTask(wf => wf.HumanTask, wf => new HumanTaskInput<HumanTaskOutput> { });
```

### JSON JQ Transform Task

```csharp
public JsonJqTransformTaskModel<JqInput, JqOutput> TransformTask { get; set; }

_builder.AddTask(
    wf => wf.TransformTask,
    wf => new JqInput { QueryExpression = ".data | map(.name)", Data = wf.Input.Items }
);
```

### PassThrough Task (Raw Definition)

Fallback for unsupported task types:

```csharp
_builder.AddTasks(new WorkflowTask
{
    Name = "custom_task",
    TaskReferenceName = "custom_ref",
    Type = "CUSTOM",
    InputParameters = new Dictionary<string, object> { ["key"] = "value" }
});
```

### Optional Tasks

Workflow continues on failure:

```csharp
_builder.AddTask(wf => wf.OptionalTask, wf => new OptionalTaskRequest { }).AsOptional();
```

## Registration & Configuration

### Service Registration

```csharp
services
    .AddConductorSharp(baseUrl: configuration.GetValue<string>("Conductor:BaseUrl"))
    .SetBuildConfiguration(new BuildConfiguration
    {
        DefaultOwnerApp = configuration.GetValue<string>("Conductor:BuildConfiguration:DefaultOwnerApp") ?? "my-app",
        DefaultOwnerEmail = configuration.GetValue<string>("Conductor:BuildConfiguration:DefaultOwnerEmail") ?? "team@example.com",
    })
    .AddExecutionManager(
        maxConcurrentWorkers: configuration.GetValue<int?>("Conductor:MaxConcurrentWorkers") ?? 10,
        sleepInterval: configuration.GetValue("Conductor:SleepInterval", 1000),
        longPollInterval: configuration.GetValue("Conductor:LongPollInterval", 1000),
        domain: null,
        typeof(Program).Assembly
    )
    .UseBetaExecutionManager()
    .AddPipelines(pipelines =>
    {
        pipelines.AddCustomBehavior(typeof(MyCustomBehavior<,>));
        pipelines.AddExecutionTaskTracking();
        pipelines.AddContextLogging();
        pipelines.AddRequestResponseLogging();
        pipelines.AddValidation();
    })
    .AddConductorSharpPatterns();
```

### Assembly-Based Registration (Preferred)

Rather than registering each handler and workflow manually, scan the assembly automatically:

```csharp
// Extension method — define once and reuse across all modules
public static IServiceCollection RegisterAllConductorPartsFromAssembly(
    this IServiceCollection services, Assembly assembly)
{
    return services
        .RegisterWorkflowsFromAssembly(assembly)
        .RegisterWorkersFromAssembly(assembly)
        .AddMediatR(config => config.RegisterServicesFromAssembly(assembly));
}

// Usage
services.RegisterAllConductorPartsFromAssembly(typeof(Program).Assembly);
```

Manual registration (for individual cases):
```csharp
services.RegisterWorkerTask<MyTaskHandler>(options =>
{
    options.OwnerEmail = "team@example.com";
    options.Description = "My task description";
});
services.RegisterWorkflow<MyWorkflow>();
```

### Multiple Conductor Instances

```csharp
services
    .AddConductorSharp(baseUrl: "http://primary:8080")
    .AddAlternateClient(
        baseUrl: "http://secondary:8080",
        key: "Secondary",
        apiPath: "api",
        ignoreInvalidCertificate: false
    );

// Resolve via keyed services
public class MyService([FromKeyedServices("Secondary")] IWorkflowService secondaryService) { }
```

### Poll Timing Strategies

```csharp
// Default: inverse exponential backoff
.AddExecutionManager(...)

// Constant interval
.AddExecutionManager(...)
.UseConstantPollTimingStrategy()
```

### Health Checks

```csharp
builder.Services.AddHealthChecks()
    .AddCheck<ConductorSharpHealthCheck>("conductor-worker");

// In execution manager chain:
.SetHealthCheckService<InMemoryHealthService>()  // default
// or
.SetHealthCheckService<FileHealthService>()      // persists to CONDUCTORSHARP_HEALTH.json
```

## API Services

| Service | Description |
|---|---|
| `IWorkflowService` | Start, pause, resume, terminate workflows |
| `ITaskService` | Update tasks, get logs, poll for tasks |
| `IMetadataService` | Manage workflow/task definitions |
| `IAdminService` | Admin operations |
| `IEventService` | Event handlers |
| `IQueueAdminService` | Queue administration |
| `IWorkflowBulkService` | Bulk workflow operations |
| `IHealthService` | Conductor server health |
| `IExternalPayloadService` | External payload storage |

## Patterns Package

```csharp
.AddConductorSharpPatterns()   // Adds WaitSeconds, ReadWorkflowTasks
.AddCSharpLambdaTasks()        // Adds C# lambda task support
```

### WaitSeconds Task

```csharp
public WaitSeconds WaitTask { get; set; }

_builder.AddTask(wf => wf.WaitTask, wf => new WaitSecondsRequest { Seconds = 30 });
```

### ReadWorkflowTasks Task

```csharp
public ReadWorkflowTasks ReadTasks { get; set; }

_builder.AddTask(
    wf => wf.ReadTasks,
    wf => new ReadWorkflowTasksInput
    {
        WorkflowId = wf.Input.TargetWorkflowId,
        TaskNames = "task1,task2"
    }
);
```

### C# Lambda Tasks

Execute C# code inline (no JavaScript needed):

```csharp
public CSharpLambdaTaskModel<LambdaInput, LambdaOutput> InlineLambda { get; set; }

_builder.AddTask(
    wf => wf.InlineLambda,
    wf => new LambdaInput { Value = wf.Input.Value },
    input => new LambdaOutput { Result = input.Value.ToUpperInvariant() }
);
```

## Kafka Cancellation Notifier

```csharp
.AddKafkaCancellationNotifier(
    kafkaBootstrapServers: "localhost:9092",
    topicName: "conductor.status.task",
    groupId: "my-worker-group",
    createTopicOnStartup: true
)
```

## Toolkit CLI

Generate C# models from existing Conductor task/workflow definitions.

```bash
# conductorsharp.yaml
baseUrl: http://localhost:8080
apiPath: api
namespace: MyApp.Generated
destination: ./Generated

# Commands
dotnet-conductorsharp                          # all tasks and workflows
dotnet-conductorsharp -n domain_get_customer   # filter by name
dotnet-conductorsharp -e team@example.com      # filter by owner email
dotnet-conductorsharp --no-tasks               # skip tasks
dotnet-conductorsharp --dry-run                # preview only
```

## Conventions

### Naming

- **Domain-prefix** all task and workflow names using `snake_case`: `access_rpd_get_device`, `order_validate_input`
- Use `[OriginalName("domain_action_description")]` on every task handler and workflow class
- Task/workflow names: `snake_case` (all lowercase with underscores)
- C# class names: PascalCase, semantically matching the `[OriginalName]`
- Use `nameof()` for switch case keys when discriminating on enum values: `[nameof(ActionType.Install)]`

### File Organization

Split workflows across partial classes. Keep request/response models in the same file as the handler:

```
src/
  Workflows/
    ResourcePreparation/
      ResourcePreparation.cs               # Class definition + In/Out + task properties
      ResourcePreparationForInstall.cs     # partial — BuildInstallFlow()
      ResourcePreparationForRemoval.cs     # partial — BuildRemovalFlow()
  Tasks/
    GetDevicesFromInventory/
      GetDevicesFromInventory.cs           # Handler + Request + Response in one file
```

### Explicit Types in AddTask Lambdas

Always use explicit type names in `AddTask` and `SetOutput` lambdas — never target-typed `new()`. ConductorSharp's expression builder requires the concrete type to generate the correct Conductor task definition, and `new()` produces an analyzer warning.

```csharp
// Wrong
_builder.AddTask(wf => wf.GetDevices, wf => new() { OrderId = wf.Input.OrderId });
_builder.SetOutput(wf => new() { ResourceId = wf.GetDevices.Output.ResourceId });

// Correct
_builder.AddTask(wf => wf.GetDevices, wf => new GetDevicesFromInventory.Request() { OrderId = wf.Input.OrderId });
_builder.SetOutput(wf => new ResourcePreparationOutput() { ResourceId = wf.GetDevices.Output.ResourceId });
```

### Validation

Use data annotation attributes on request models, not validation logic in handlers:

```csharp
public class GetCustomerRequest : IRequest<GetCustomerResponse>
{
    [Required]
    public required string CustomerId { get; set; }
}
```

Register `AddValidation()` in the pipeline to enforce automatically.

### Failure Workflows

Define a shared failure workflow per domain and reference it via `[WorkflowMetadata]`:

```csharp
[WorkflowMetadata(FailureWorkflow = typeof(FailAllRunningReports))]
```

## TMF652 Trigger + Signal-Based Completion Pattern (SOM → ROM)

When a SOM fulfillment needs to trigger ROM workflows and wait for completion, **do not poll inside a worker**. The platform (ResourceOrderingEngine) sends a Conductor signal when a ROM order reaches a terminal state. Use a `ROM_PollAndRetry` sub-workflow that waits for this signal.

### The Three-Part Pattern

**1. Trigger worker** — fire the resource order, return `RomOrderId` only (no polling):

```csharp
public sealed class Handler(
    IResourceCatalogManagement4ApiClient catalogClient,
    IResourceOrderingManagement4ApiClient romClient
) : TaskRequestHandler<Request, Response>
{
    public override async Task<Response> Handle(Request request, CancellationToken cancellationToken)
    {
        var specification = await catalogClient.GetResourceSpecificationAsync(MyResource.Id, cancellationToken);

        var resource = new ResourceRefOrValue
        {
            ResourceSpecification = new ResourceSpecificationRef { Id = MyResource.Id, Name = MyResource.Name }
        };
        var inputProxy = resource.ToEntityProxy<MyResourceEntityProxy>(specification);
        inputProxy.SomeField = request.SomeValue;

        var order = await romClient.CreateResourceOrderAsync(new ResourceOrder_Create
        {
            State = ResourceOrderStateType.Acknowledged,
            Description = "...",
            OrderItem =
            [
                new ResourceOrderItem
                {
                    Id = "1", Quantity = 1,
                    Action = OrderItemActionType.Add,
                    State = ResourceOrderItemStateType.Initial,
                    Resource = resource,
                    ResourceSpecification = new ResourceSpecificationRef { Id = MyResource.Id, Name = MyResource.Name }
                }
            ]
        }, cancellationToken);

        return new Response
        {
            RomOrderId = order.Id ?? throw new InvalidOperationException("Resource order created without an ID.")
        };
    }
}
```

**2. `ROM_PollAndRetry` sub-workflow** — waits for the platform signal, then reads inventory (`ConductorSharp.Patterns` v4+ required for `SignalWait`):

```csharp
// using ConductorSharp.Patterns.Model;
// using ConductorSharp.Patterns.Workflows;

[OriginalName("my_rom_poll_and_retry")]
public class ROM_PollAndRetry(
    WorkflowDefinitionBuilder<ROM_PollAndRetry, RomPollAndRetryInput, RomPollAndRetryOutput> builder
) : Workflow<ROM_PollAndRetry, RomPollAndRetryInput, RomPollAndRetryOutput>(builder)
{
    public required SignalWait WaitForRomOrderCompletion { get; set; }
    public required ROM_CheckResourceStatus.Handler VerifyRomResources { get; set; }

    public override void BuildDefinition()
    {
        _builder.AddTask(
            wf => wf.WaitForRomOrderCompletion,
            wf => new SignalWaitInput
            {
                // Platform sends this signal key when the ROM order completes
                SignalKey = $"{Constants.RomOrderCompletionSignalKeyPrefix}:{wf.Input.RomOrderId}",
            }
        );
        _builder.AddTask(
            wf => wf.VerifyRomResources,
            wf => new() { RomOrderId = wf.Input.RomOrderId, ExpectedStatus = wf.Input.ExpectedStatus }
        );
        _builder.SetOutput(wf => new()
        {
            ResourceId = wf.VerifyRomResources.Output.ResourceId,
            ResourceIds = wf.VerifyRomResources.Output.ResourceIds,
            Completed = wf.VerifyRomResources.Output.Completed,
        });
    }
}
```

`RomOrderCompletionSignalKeyPrefix = "rom_order"` — define this as a constant and add `AddConductorSharpPatterns()` to the DI setup.

**3. `ROM_CheckResourceStatus` worker** — reads inventory resources associated with the order:

```csharp
// Queries IResourceInventoryManagement4ApiClient.ListResourcesAsync with
// RelatedResourceOrderItemResourceOrderId = [romOrderId] per order item.
// Returns ResourceIds of resources matching the expected status.
```

**4. Read attributes worker** — after the poll, read characteristics from inventory using the `ResourceId`:

```csharp
var resource = await rimClient.GetResourceAsync(request.ResourceId, cancellationToken);
var proxy = resource.ToEntityProxy<MyResourceEntityProxy>(specification);
// Read proxy properties — output characteristics are in inventory, not in the order
```

### SOM Fulfillment Workflow Structure

Chain multiple ROM orders sequentially in the SOM workflow:

```
TriggerA → ROM_PollAndRetry → ReadAttributesA → TriggerB → ROM_PollAndRetry → ... → RetrieveOutputAttributes
```

Each `ROM_PollAndRetry` is a sub-workflow property typed as `ROM_PollAndRetry` — multiple instances are allowed; ConductorSharp uses the property name as the task reference name.

### Entity Proxy for TMF Characteristics

Generated entity proxies (`*EntityProxy`) provide type-safe access to TMF resource characteristics. They work on both inventory entities (`Resource`) and order entities (`ResourceRefOrValue`). Setting a proxy property writes directly to the entity's `ResourceCharacteristic` list in-place.

```csharp
// Set characteristics on a new resource for an order (order entity)
var resource = new ResourceRefOrValue { ... };
var proxy = resource.ToEntityProxy<MyResourceEntityProxy>(specification);
proxy.Name = "value";   // writes to resource.ResourceCharacteristic

// Read characteristics from a resource inventory entity (after ROM_PollAndRetry)
var inventoryResource = await rimClient.GetResourceAsync(resourceId, cancellationToken);
var outputProxy = inventoryResource.ToEntityProxy<MyResourceEntityProxy>(specification);
var value = outputProxy.Name;
```

Both `ResourceRefOrValue` (order) and `Resource` (inventory) have a `ToEntityProxy<T>` extension method generated in `EntityProxyFactory`. Output characteristics come from inventory (read via `IResourceInventoryManagement4ApiClient`), **not** from the order item — the platform writes output attributes to the inventory resource upon order completion.

**Characteristic type coercion:** Output IDs that are semantically `int` (e.g. `CustomerID`) are stored as `string` in TMF characteristics. Always parse with `InvariantCulture`:

```csharp
int customerId = int.Parse(outputProxy.CustomerID, CultureInfo.InvariantCulture);
```

### Avoid Tasks for Trivial Computations

Do not create a Conductor worker task solely to perform a simple inline computation (e.g. multiplying a value by a constant). Compute it inside the worker that uses the result. A Conductor task adds serialization overhead and network round-trips that are not justified for logic that fits on one line.

```csharp
// Wrong: separate Conductor task just to multiply
// Right: compute inline in the worker that uses it
inputProxy.SimultaneousCalls = request.MaxSimultaneousCalls * SimultaneousCallsMultiplier;
```

### Cross-Cluster Constraint

`SignalWait` requires SOM and ROM to connect to the **same Conductor server**. If SOM and ROM run on separate K8s clusters with separate Conductor instances, the `rom_order:{RomOrderId}` signal sent by ROM's Conductor never reaches SOM's waiting task — the `ROM_PollAndRetry` sub-workflow will hang indefinitely.

| Option | Mechanism | Notes |
|---|---|---|
| **A — Poll TMF652** | SOM periodically calls `GET /resourceOrder/{id}` until terminal state, then reads inventory via TMF639 | Order state is authoritative; requires `WaitSeconds` + retry loop |
| **B — Poll TMF639** | SOM periodically queries resource inventory until resource appears with expected status | Infers completion from inventory state rather than order state |
| **C — Shared Conductor** | Single Conductor server accessible from both clusters | No code changes; operational complexity shifts to infrastructure |

> **⚠ Verify topology before implementing fulfillment:** If SOM and ROM are on separate clusters, choose an alternative and update the sub-workflow design before writing any fulfillment code.

## Integration Testing

Integration tests submit workflows to a **real Conductor server** running in Docker (via Testcontainers). There are no mocks for workflow execution.

### Infrastructure

Create a thin factory subclass — no overrides needed:

```csharp
public sealed class MyIntegrationTestFactory : IntegrationTestFactory<Program> { }
```

Wire it up as an xUnit collection fixture with parallelisation disabled:

```csharp
[CollectionDefinition(Name, DisableParallelization = true)]
public sealed class IntegrationTestCollection : ICollectionFixture<MyIntegrationTestFactory> {
    public const string Name = "Integration";
}
```

`IntegrationTestFactory<TProgram>` spins up (via Testcontainers):
- Conductor server (with Redis backend and PostgreSQL)
- PostgreSQL database
- Redis
- All TMF-based domain microservices (service/resource catalog, ordering, inventory, party, geographic site/address management)

The application under test (`Program`) is started via `WebApplicationFactory<TProgram>` with its configuration pointing at the containers. Authentication is replaced with a no-op test handler.

### Running a Workflow

```csharp
[Collection(IntegrationTestCollection.Name)]
public class MyWorkflowTests(MyIntegrationTestFactory integrationTestFactory) {
    [Fact]
    public async Task MyWorkflow_Should_Complete() {
        SimpleWorkflowStarter<Program> workflowStarter = new(integrationTestFactory);

        var workflow = await workflowStarter.RunWorkflow(
            new StartWorkflowRequest {
                Name = "my_workflow_name",
                Input = new MyWorkflowInput { /* ... */ }.ToConductorDictionary()
            },
            null,    // optional: Func<Workflow, string> to assert a specific output value on completion
            false    // expectFailure: set true when the workflow is expected to fail
        );
    }
}
```

`RunWorkflow` starts the workflow on Conductor, then polls `GetExecutionStatusAsync` every second until it reaches a terminal state. `ToConductorDictionary()` serialises the input object to the Conductor-compatible dictionary format (snake_case keys, Newtonsoft serialisation).

### Assertion Styles

**Style 1 — Output string search** (`using Shared.TestUtilities.Extensions`):

Recursively searches all task `OutputData` (including nested dicts, arrays, and `JsonElement`) for an exact string match. Use when testing that a specific value was produced anywhere in the workflow.

```csharp
// Passes if any task output contains the exact string "ABCDÉ"
workflow.ShouldContainOutputString("ABCDÉ", "Expected upper-path output.");

// Passes if NO task output contains the string
workflow.ShouldNotContainOutputString("abcdé", "Lower-path output should not exist.");

// Returns the matching Task, or null — useful for further assertions
var task = workflow.FindTaskWithOutputString("some_value");

// Dumps all tasks as a formatted string for manual debugging (also included in failure messages)
string dump = workflow.DumpTasks();
// → "- ref='task_ref', def='task_def', status='COMPLETED', output={...}"
```

Failure messages automatically include a `DumpTasks()` dump, showing ref name, def name, status, and output (truncated at 800 chars) for every task.

**Style 2 — Exact output + task sequence** (Shouldly on workflow properties):

Use when the workflow contract (output shape and task order) is what matters, not specific string values.

```csharp
// Assert the workflow's final output matches exactly
workflow.Output.ShouldBe(new MyWorkflowOutput { /* ... */ }.ToConductorDictionary());

// Assert the exact sequence of task definition names (order matters)
workflow.Tasks.Select(t => t.TaskDefName).ShouldBe([
    "my_first_task",
    "my_second_task",
]);
```

**Style 3 — Failed workflow error extraction**:

When `expectFailure: true`, extract structured error messages from the failed task or workflow output:

```csharp
var workflow = await workflowStarter.RunWorkflow(request, null, expectFailure: true);
var errors = workflow.ExtractErrorMessagesFromFailedWorkflow();
// Extracts from: failed task's output_data["error_message"], output_data["errors"][],
// or output_data["response"]["errors"][]
```

### FakeEngine (TMF Order Simulation)

For workflows that interact with TMF service/resource orders, `IntegrationTestFactory` starts a `FakeEngine` background worker. It polls pending service and resource orders every second and auto-completes them (creating inventory entries for `Add` actions, linking existing entities for `Modify`/`Delete`). This unblocks workflows that wait on order completion without needing a real order management engine.

`FakeEngine` is only relevant when your workflow submits TMF orders. Simple workflows (like a `HelloWorldWorkflow`) don't need it and it runs transparently in the background.

## Known Limitations

- Conductor **events** are not supported by the library
- `DoWhileTaskModel` provides no strongly typed output (`NoOutput`)
- `LambdaTaskModel` output is accessed via `Output.Result.Property` (extra `.Result` level)
- Dictionary indexing on arbitrary types (non-`Dictionary<,>`) is not supported in expressions
- **`Nullable<T>.Value` access in expression-tree lambdas does not translate.** The visitor emits a fictitious path (e.g. `${task.output.field.value}`) that resolves to `default(T)` at runtime — *no compile error, silent data corruption*. If a downstream task's `Request` field is non-nullable but the upstream `Response` is `T?`, **don't** bridge with `!.Value` in the workflow expression. Instead, propagate the nullable type into the `Request` (e.g. `int?` end-to-end) and add a defensive null check in the handler. The same applies to `GetValueOrDefault()` and other method calls; only plain property chaining works.
- **Switch task case values are JSON strings.** The `SwitchCaseValue` expression must evaluate to a string at runtime, and `DecisionCases<>` keys are strings. The discriminator field on the source `Response` should therefore be typed as `string` (with `const string` values for the cases) or as an `enum` (with `[nameof(EnumValue)]` keys). A `bool` field would technically serialize to `"true"`/`"false"` but is non-idiomatic and couples the workflow to .NET's bool serialization — prefer explicit `string` constants.
