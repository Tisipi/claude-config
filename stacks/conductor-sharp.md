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

**Option A — Nested `In`/`Out` classes:** input and output are inner classes of the workflow. Keeps everything self-contained, works well with `partial class`.

**Option B — Flat external classes (default):** input and output are separate top-level classes named `<WorkflowName>Input` / `<WorkflowName>Output`. More verbose but easier to reference from outside the workflow class and to reuse as a base class. Access via `wf.WorkflowInput` is identical in both options.

Use Option B unless the project already uses Option A — don't mix within a project.

**Option A example (nested classes):**

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
        public required Device Device { get; init; }
        public required string Intent { get; set; }
    }

    // Task properties — become strongly-typed references in BuildDefinition
    public required GetDevicesFromInventory GetDevices { get; set; }
    public required SwitchTaskModel DecideAction { get; set; }
}
```

**Option B example (flat classes, default):**

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
            wf => new GetDevicesFromInventory.Request() { OrderId = wf.WorkflowInput.OrderId }
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
        wf => new GetDevicesFromInventory { OrderId = wf.WorkflowInput.OrderId }
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
        Device = wf.GetDevices.Output.Device,
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
    public required Device Device { get; set; }
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
- Override with `[JsonProperty("custom_name")]` (Newtonsoft, takes precedence) or `[JsonPropertyName("custom_name")]`; the name is used verbatim in the generated expression, so a dotted name such as `"prepare_output.order_data.id"` binds a path into the workflow input (see *Multi-Phase Order Orchestration*)
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

C# property access and string interpolation auto-translates to Conductor expressions. Use `wf.WorkflowInput` to reference the workflow input (`wf.Input` is inherited from the task model and generates the same expression, but reads like a task input):

```csharp
// C#
CustomerName = $"{wf.GetCustomer.Output.FirstName} {wf.GetCustomer.Output.LastName}"
Address = wf.WorkflowInput.Address   // wf.WorkflowInput references the workflow's input class

// Generated Conductor JSON
"customer_name": "${get_customer.output.first_name} ${get_customer.output.last_name}",
"address": "${workflow.input.address}"
```

**Supported expression features:**

- **Property chaining**: `wf.Task.Output.Field` — plain member access only; no method calls and no `Nullable<T>.Value` (see Known Limitations)
- **String interpolation**: `$"{wf.Task.Output.Name}"`
- **String concatenation**: `1 + "Str_" + wf.WorkflowInput.Value`
- **Type casting**: `((FullName)wf.Task.Output.Name).FirstName` → `${task.output.name.first_name}`
- **Dictionary indexing**: `wf.WorkflowInput.Dictionary["key"].Property` → `${workflow.input.dictionary['key'].property}`
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
_builder.AddTask(wf => wf.MyTask, wf => new MyTaskRequest { Input = wf.WorkflowInput.Value });
```

### Sub-Workflow Task

Declare with `SubWorkflowTaskModel<TInput, TOutput>`:

```csharp
public SubWorkflowTaskModel<ChildWorkflowInput, ChildWorkflowOutput> ChildWorkflow { get; set; }

_builder.AddTask(wf => wf.ChildWorkflow, wf => new ChildWorkflowInput { OrderId = wf.WorkflowInput.OrderId });
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
        TaskInput = new ExpectedInput { OrderId = wf.WorkflowInput.OrderId },
        TaskToExecute = wf.WorkflowInput.TaskName
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
    wf => new DoWhileInput { Value = wf.WorkflowInput.Loops },
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
    wf => new LambdaInput { Value = wf.WorkflowInput.Value },
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
            Device = wf.GetDevices.Output.Device,
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
    wf => new JqInput { QueryExpression = ".data | map(.name)", Data = wf.WorkflowInput.Items }
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

### Assembly-Based Registration

ConductorSharp registers per type (`RegisterWorkerTask<T>()`, `RegisterWorkflow<T>()`). For many types, write a small helper once that scans the assembly (workflows implement `IConfigurableWorkflow`, workers implement `IWorker`) and calls the generic methods by reflection:

```csharp
public static void RegisterAllWorkflows(this IServiceCollection services, Assembly assembly)
{
    var register = typeof(WorkflowRegistrationExtensions).GetMethod("RegisterWorkflow");
    foreach (var type in assembly.GetTypes().Where(t => typeof(IConfigurableWorkflow).IsAssignableFrom(t) && !t.IsAbstract))
    {
        register!.MakeGenericMethod(type).Invoke(null, [services, null]);
    }
}
// RegisterAllWorkerTasks: same with IWorker and TaskRegistrationExtensions.RegisterWorkerTask
```

Handlers (MediatR) are discovered through the assemblies passed to `AddExecutionManager(..., typeof(Program).Assembly)`.

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
        WorkflowId = wf.WorkflowInput.TargetWorkflowId,
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
    wf => new LambdaInput { Value = wf.WorkflowInput.Value },
    input => new LambdaOutput { Result = input.Value.ToUpperInvariant() }
);
```

### SignalWait (wait for an external event)

Pauses a workflow until something outside Conductor sends a signal, without holding a worker. `SignalWait` is a sub-workflow (`signal_wait`) of `ConductorSharp.Patterns`.

```csharp
.AddSignalWait<MySignalStore>("my_app")   // ISignalStore implementation + SignalService + sweeper; prefix names the registered tasks

public required SignalWait WaitForEvent { get; set; }
_builder.AddTask(wf => wf.WaitForEvent, wf => new SignalWaitInput { SignalKey = $"order:{wf.WorkflowInput.OrderId}" });

// Anywhere else (endpoint, listener): ISignalService
await signalService.SendSignalAsync($"order:{orderId}", TaskResultStatus.COMPLETED, outputData: null, ct);
```

- `InMemorySignalStore` is for development and tests only; production needs a persistent `ISignalStore`
- A signal sent before the workflow waits is stored and delivered later; `SignalSweeperService` completes stragglers
- `SignalWaitOutput` is empty: read results from the system of record after the wait
- Sender and workflow must talk to the same Conductor server and share the store
- Design guidance and failure handling: *Waiting for resource order completion*

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

- **Domain-prefix** all task and workflow names using `snake_case`: `billing_get_invoice`, `orders_validate_input`
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
_builder.AddTask(wf => wf.GetDevices, wf => new() { OrderId = wf.WorkflowInput.OrderId });
_builder.SetOutput(wf => new() { ResourceId = wf.GetDevices.Output.ResourceId });

// Correct
_builder.AddTask(wf => wf.GetDevices, wf => new GetDevicesFromInventory.Request() { OrderId = wf.WorkflowInput.OrderId });
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

### Avoid Tasks for Trivial Computations

Do not create a Conductor task solely for a one-line computation (multiplying by a constant, concatenating a name). A task adds serialization and a network round-trip; compute it inside the worker that uses the result:

```csharp
proxy.MaxConnections = request.MaxUsers * ConnectionsPerUser;   // not a separate "multiply" task
```

### Failure Workflows

Define a shared failure workflow per domain and reference it via `[WorkflowMetadata]`:

```csharp
[WorkflowMetadata(FailureWorkflow = typeof(FailAllRunningReports))]
```

## Error Handling

Let exceptions propagate out of workers: a failing task fails the workflow. When callers need a machine-readable outcome, throw `StructuredErrorException` (`ConductorSharp.Engine.Exceptions`): it carries a `Code`, a `Reason`, an optional `ReferenceError` and an optional inner exception.

Map exceptions to codes in **one place**, a MediatR pipeline behavior wrapped around every task, instead of try/catch in each worker:

```csharp
public sealed class ErrorMappingBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : notnull
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        try
        {
            return await next();
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (StructuredErrorException)
        {
            throw;
        }
        catch (Exception exception)
        {
            throw ErrorMapper.FromUnhandled(exception);   // switch on exception TYPE, never on message text
        }
    }
}

pipelines.AddCustomBehavior(typeof(ErrorMappingBehavior<,>));   // register first so it also wraps AddValidation()
```

- Error codes are constants (validation, southbound/transport, timeout, internal), not string literals
- Southbound clients throw their own typed exceptions; the mapper translates them (HTTP timeouts to the timeout code, other transport failures to the southbound code, data-annotation and parsing failures to the validation code)
- Aggregate exceptions: flatten, then pick the most specific code
- Never swallow exceptions in a worker to "keep the workflow going"; use `.AsOptional()` on the task when failure is acceptable, and check the outcome explicitly afterwards (see *Waiting for resource order completion*)

## Multi-Phase Order Orchestration

Applies to apps that implement TM Forum style order orchestration on Conductor: a **service layer** receives service orders (TMF641) and creates resource orders (TMF652); a **resource layer** executes each resource order against southbound systems and records the result in resource inventory (TMF639). Many apps contain both layers, as one host or as two hosts sharing a common project. Skip this chapter for plain Conductor workflows.

The names of the context keys the platform passes to a phase workflow (`item`, `service_id`, `prepare_output`, ...) are defined by the orchestration platform that starts the phase workflows. The examples use the common ones; check the platform documentation for the exact names.

### Operations and phases

Each layer implements the operations **Add / Modify / Delete** per specification. Every operation consists of three workflows, called phases, that the platform runs in this order:

| Phase | Purpose | Side effects |
|---|---|---|
| **Preparation** | Collect everything the later phases need: extract characteristics from the order item, validate them, enrich them (catalog defaults, inventory lookups, current service snapshot). Output is typed data. | None on external systems |
| **Feasibility** | Pre-flight checks that the change can be made (referenced service exists, not terminated, capacity available) | None |
| **Fulfillment** | Do the work: trigger resource orders, call southbound systems, write results to inventory | Yes |

- All three phases always exist for every operation. A phase without work contains a single no-op worker: Conductor rejects a workflow definition without tasks
- A failure in preparation or feasibility rejects the order before anything was changed. Put every check that can fail cheaply there, before fulfillment starts changing systems
- Phase workflows are named by convention, with the names held in constants: `<layer>_<operation>_<kind>_<phase>` (for example `mailbox_add_resource_preparation`)

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
- Feasibility and fulfillment can read the outputs of the phases before them through the same dotted names. Whether fulfillment can also read *feasibility* output depends on whether the platform exposes it; if it does not, carry the data in the preparation output instead
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

### Layout of an orchestration app

```
src/
  <Product>.<Layer>.Application/            # one host per layer, or one host containing both
    Program.cs
    <Resource or Service>/
      Common/        # validation rules, shared workers and input base classes
      Add/  Modify/  Delete/
        Workflows/   # <Op>Preparation, <Op>Feasibility, <Op>Fulfillment (+ their Input/Output)
        Workers/     # one file per worker: Request, Response, Handler
    Common/          # no-op worker, error mapping behavior, shared constants usage
    Mappings/        # workflow mappings and the startup service
  <Product>.Commons/                         # constants (workflow, worker, error code names), options, shared hosting extensions
  <Product>.Domain/                          # specifications and generated typed proxies; never edited by hand
test/
  <Product>.Application.Tests/
    Unit/            # workers, validation rules, error mapping, workflow build tests
    Integration/     # workflows against a real Conductor server
    Support/
```

## Testing

Workflows run on a Conductor server, so test on three levels.

**1. Worker unit tests.** Construct the `Handler` with fakes or stubs for its clients and call `Handle(request, ct)`. Assert on the response, on thrown exceptions (`StructuredErrorException.Code`), and on what the fake recorded. Cover each validation rule and each branch of a worker.

**2. Workflow definition tests.** Create the workflow with its builder from a service provider (the same registration as production, without a Conductor server) and build its definition, so broken expressions and unsupported constructs fail in a unit test:

```csharp
var builder = provider.GetRequiredService<WorkflowDefinitionBuilder<MyWorkflow, MyInput, MyOutput>>();
var workflow = (MyWorkflow)Activator.CreateInstance(typeof(MyWorkflow), builder)!;   // `new` does not compile when task properties are `required`
var definition = workflow.GetDefinition();                                         // builds the expressions; throws on unsupported constructs
```

  The generated definition is also the place to pin a contract, for example that an input binding resolves to the expected path:
  `definition.Tasks[0].InputParameters["domain_name"].ShouldBe("${workflow.input.prepare_output.order_data.domain_name}")`.

  Add one test that enumerates every workflow type by reflection (`[MemberData]`) and builds it, plus the mapping coverage test (every workflow is mapped), plus a test that pins the phase output contract (the dotted input names bind to existing output properties).

**3. Integration tests against a real Conductor server.** Start Conductor (with its Redis and database dependencies) in containers (Testcontainers), start the app through `WebApplicationFactory<Program>` with configuration pointing at the containers, stub external HTTP systems with WireMock, then run the workflow:

```csharp
[CollectionDefinition(Name, DisableParallelization = true)]
public sealed class IntegrationCollection : ICollectionFixture<IntegrationTestFactory> { public const string Name = "Integration"; }

var workflowId = await workflowService.StartAsync(new StartWorkflowRequest
{
    Name = NamingUtil.NameOf<MailboxAddPreparation>(),
    Input = new Dictionary<string, object> { ["item"] = itemAsDictionary }
}, ct);

var workflow = await WaitUntilTerminalAsync(workflowId, ct);   // poll IWorkflowService.GetExecutionStatusAsync(id, includeTasks: true) every second, with a timeout
workflow.Status.ShouldBe(WorkflowStatus.COMPLETED);
```

- Assert the **task sequence** (`workflow.Tasks.Select(t => t.TaskDefName)`) and the **output**; the pair is the workflow's contract
- For expected failures assert on the failing task's output (`error_message`, `errors`) or on the `StructuredErrorException` code, not only on the status
- Multi-phase flows: run the phases in order with the earlier output nested under the phase key (`{ "prepare_output": {...} }`) as the platform would
- Workflows that wait on resource orders need something that completes those orders. In integration tests run a small fake order-completion worker (polls pending resource orders, creates or updates inventory, marks the order completed) so the wait unblocks without the real order platform; or send the signal from the test
- Containers are slow: one collection fixture for the whole suite, parallelisation disabled, workflows named in constants so tests never hard-code strings


## Known Limitations

- Conductor **events** are not supported by the library
- `DoWhileTaskModel` provides no strongly typed output (`NoOutput`)
- `LambdaTaskModel` output is accessed via `Output.Result.Property` (extra `.Result` level)
- Dictionary indexing on arbitrary types (non-`Dictionary<,>`) is not supported in expressions
- **`Nullable<T>.Value` access in expression-tree lambdas does not translate.** The visitor emits a fictitious path (e.g. `${task.output.field.value}`) that resolves to `default(T)` at runtime — *no compile error, silent data corruption*. If a downstream task's `Request` field is non-nullable but the upstream `Response` is `T?`, **don't** bridge with `!.Value` in the workflow expression. Instead, propagate the nullable type into the `Request` (e.g. `int?` end-to-end) and add a defensive null check in the handler. The same applies to `GetValueOrDefault()` and other method calls; only plain property chaining works.
- **Switch task case values are JSON strings.** The `SwitchCaseValue` expression must evaluate to a string at runtime, and `DecisionCases<>` keys are strings. The discriminator field on the source `Response` should therefore be typed as `string` (with `const string` values for the cases) or as an `enum` (with `[nameof(EnumValue)]` keys). A `bool` field would technically serialize to `"true"`/`"false"` but is non-idiomatic and couples the workflow to .NET's bool serialization — prefer explicit `string` constants.
