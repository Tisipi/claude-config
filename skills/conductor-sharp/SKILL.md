---
name: conductor-sharp
description: ConductorSharp (.NET client for Netflix/Orkes Conductor) development guide. Use when writing or changing Conductor workflows, task handlers, workflow definitions, execution-manager configuration, SignalWait, the Toolkit scaffolder, multi-phase order orchestration (preparation, feasibility, fulfillment, TMF641/TMF652) or tests for these. Covers task types, registration, patterns, error handling, conventions and known limitations.
---

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
- Override with `[JsonProperty("custom_name")]` (Newtonsoft, takes precedence) or `[JsonPropertyName("custom_name")]`; the name is used verbatim in the generated expression, so a dotted name such as `"prepare_output.order_data.id"` binds a path into the workflow input (see [orchestration.md](orchestration.md))
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
- Never swallow exceptions in a worker to "keep the workflow going"; use `.AsOptional()` on the task when failure is acceptable, and check the outcome explicitly afterwards (see *Waiting for resource order completion* in [orchestration.md](orchestration.md))

## Known Limitations

- Conductor **events** are not supported by the library
- `DoWhileTaskModel` provides no strongly typed output (`NoOutput`)
- `LambdaTaskModel` output is accessed via `Output.Result.Property` (extra `.Result` level)
- Dictionary indexing on arbitrary types (non-`Dictionary<,>`) is not supported in expressions
- **`Nullable<T>.Value` access in expression-tree lambdas does not translate.** The visitor emits a fictitious path (e.g. `${task.output.field.value}`) that resolves to `default(T)` at runtime — *no compile error, silent data corruption*. If a downstream task's `Request` field is non-nullable but the upstream `Response` is `T?`, **don't** bridge with `!.Value` in the workflow expression. Instead, propagate the nullable type into the `Request` (e.g. `int?` end-to-end) and add a defensive null check in the handler. The same applies to `GetValueOrDefault()` and other method calls; only plain property chaining works.
- **Switch task case values are JSON strings.** The `SwitchCaseValue` expression must evaluate to a string at runtime, and `DecisionCases<>` keys are strings. The discriminator field on the source `Response` should therefore be typed as `string` (with `const string` values for the cases) or as an `enum` (with `[nameof(EnumValue)]` keys). A `bool` field would technically serialize to `"true"`/`"false"` but is non-idiomatic and couples the workflow to .NET's bool serialization — prefer explicit `string` constants.

## Reference files

Read the one that matches the task; each is self-contained.

- [task-types.md](task-types.md): every task type with code (simple, sub-workflow, switch, dynamic, fork-join, do-while, lambda, wait, terminate, human, JQ, passthrough, optional)
- [configuration.md](configuration.md): service registration, assembly registration, multiple instances, polling, health checks, API services, Patterns package (WaitSeconds, ReadWorkflowTasks, C# lambda, SignalWait), Kafka cancellation, Toolkit CLI
- [orchestration.md](orchestration.md): multi-phase order orchestration: phases, data flow between phases, creating and awaiting resource orders, resource layer, rollback phases, app layout
- [testing.md](testing.md): worker unit tests, workflow definition tests, integration tests against a containerised Conductor
