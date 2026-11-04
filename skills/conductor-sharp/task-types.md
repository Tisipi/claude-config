# Task Types

Part of the ConductorSharp skill ([SKILL.md](SKILL.md)).

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
