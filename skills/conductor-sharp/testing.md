# Testing

Part of the ConductorSharp skill ([SKILL.md](SKILL.md)).

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
