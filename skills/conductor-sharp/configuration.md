# Registration & Configuration

Part of the ConductorSharp skill ([SKILL.md](SKILL.md)).

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
- `AddSignalWait` also registers the `SignalWait` workflow, the `RegisterWaiter` worker and the sweeper: do not register them again
- Signal keys are business identifiers that sender and workflow can both derive (`order:{orderId}`, `approval:{requestId}`), unique per wait; a constant prefix avoids collisions between flows
- A persistent `ISignalStore` implements five methods: `RegisterWaiterAsync`, `RegisterSignalAsync(key, status, outputData)`, `GetResolvableEntriesAsync` (waiter and signal both present), `GetPendingWaitersAsync` and `DeleteAsync`. Both registrations are upserts keyed by signal key, because either side can arrive first. `RegisterWaiter` runs with `ConcurrentExecLimit = 1` and 10 retries, but with several replicas the store itself must still be safe under concurrent calls (unique key, upsert)
- Design guidance and failure handling: *Waiting for resource order completion* in [orchestration.md](orchestration.md)

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
dotnet-conductorsharp -a my-application        # filter by owner app
dotnet-conductorsharp --no-workflows           # skip workflows
dotnet-conductorsharp -f other.yaml            # custom config file
dotnet-conductorsharp --dry-run                # preview only
```
