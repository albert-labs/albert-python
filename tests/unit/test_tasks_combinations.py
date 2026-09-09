from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from albert.collections.tasks import TaskCollection
from albert.exceptions import CombinationGenerationError
from albert.resources.interval_combinations import ExclusionRule, RuleCondition, RuleOperator
from albert.resources.tasks import BatchTask, Block, PropertyTask
from albert.resources.worker_jobs import WorkerJob, WorkerJobMetadata, WorkerJobState
from albert.utils.worker_jobs import poll_worker_job


def test_combination_generation_error_attributes():
    """Test that CombinationGenerationError preserves task, failed_blocks, and job_states."""
    task = PropertyTask(id="TASFOR123", name="Test Task")
    failed_blocks = ["BLK2", "BLK3"]
    job_states = {"BLK1": "successful", "BLK2": "failed", "BLK3": "failed"}

    err = CombinationGenerationError(
        "Combination generation failed for blocks: BLK2, BLK3",
        task=task,
        failed_blocks=failed_blocks,
        job_states=job_states,
    )

    assert err.task.id == "TASFOR123"
    assert err.failed_blocks == ["BLK2", "BLK3"]
    assert err.job_states == job_states
    assert "Combination generation failed" in str(err)


def test_create_with_combinations_rejects_non_property_task():
    """Test that create_with_combinations rejects non-PropertyTask."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    batch_task = BatchTask(id="TASMAN1", name="Batch Lab Task")
    with pytest.raises((TypeError, ValidationError)):
        tasks_collection.create_with_combinations(task=batch_task)  # type: ignore[arg-type]


def test_generate_block_combinations_rejects_non_property_task():
    """Test that generate_block_combinations raises TypeError if task is not a PropertyTask."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    batch_task = BatchTask(id="TASMAN1", name="Batch Lab Task")
    tasks_collection.get_by_id = MagicMock(return_value=batch_task)  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="must be a PropertyTask"):
        tasks_collection.generate_block_combinations(task_id="TASMAN1", block_id="BLK1")


def test_generate_block_combinations_raises_value_error_for_missing_block():
    """Test that generate_block_combinations raises ValueError if block is missing."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    prop_task = PropertyTask(
        id="TASFOR1",
        name="Property Task",
        blocks=[Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL1"}])],
    )
    tasks_collection.get_by_id = MagicMock(return_value=prop_task)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="Block BLK2 not found"):
        tasks_collection.generate_block_combinations(task_id="TASFOR1", block_id="BLK2")


def test_poll_worker_job_raises_on_failed_state():
    """Test that poll_worker_job raises AlbertException when job fails."""
    session = MagicMock()
    job_resp = MagicMock()
    job_resp.json.return_value = {
        "albertId": "JOB123",
        "jobType": "createChildWorkflows",
        "state": "failed",
        "stateMessage": "Execution error in worker",
        "metadata": {"parentType": "TAS", "albertId": "TAS1"},
    }
    session.get.return_value = job_resp

    with pytest.raises(Exception, match="Worker job JOB123 failed: Execution error"):
        poll_worker_job(session=session, job_id="JOB123", raise_on_failure=True)


def test_poll_worker_job_returns_job_when_not_raising_on_failure():
    """Test that poll_worker_job returns the job without raising when raise_on_failure=False."""
    session = MagicMock()
    job_resp = MagicMock()
    job_resp.json.return_value = {
        "albertId": "JOB123",
        "jobType": "createChildWorkflows",
        "state": "failed",
        "stateMessage": "Execution error in worker",
        "metadata": {"parentType": "TAS", "albertId": "TAS1"},
    }
    session.get.return_value = job_resp

    job = poll_worker_job(session=session, job_id="JOB123", raise_on_failure=False)
    assert isinstance(job, WorkerJob)
    assert job.state == WorkerJobState.FAILED
    assert job.albert_id == "JOB123"


def test_generate_block_combinations_no_intervals_submits_bare_job():
    """Test that non-intervalized blocks submit a worker job without S3 upload."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    prop_task = PropertyTask(
        id="TASFOR1",
        name="Property Task",
        blocks=[Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL10"}])],
    )
    tasks_collection.get_by_id = MagicMock(return_value=prop_task)  # type: ignore[method-assign]

    # Workflow without intervalized parameters
    wfl_resp = MagicMock()
    wfl_resp.json.return_value = {
        "id": "WFL10",
        "name": "Static Workflow",
        "parameterGroupSetpoints": [
            {
                "id": "PRG1",
                "parameters": [
                    {"id": "PRM1", "value": "100", "rowId": "ROW1"},
                ],
            }
        ],
    }
    session.get.return_value = wfl_resp

    # Block rules (empty)
    tasks_collection.get_block_rules = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(rules=[], overrides=[])
    )

    # Worker job response
    job_post_resp = MagicMock()
    job_post_resp.json.return_value = {
        "albertId": "JOB999",
        "jobType": "createChildWorkflows",
        "state": "successful",
        "metadata": {
            "parentType": "TAS",
            "albertId": "TASFOR1",
            "blockId": "BLK1",
            "newWorkflowId": "WFL10",
        },
    }
    session.post.return_value = job_post_resp

    job = tasks_collection.generate_block_combinations(
        task_id="TASFOR1", block_id="BLK1", wait=False
    )

    assert job.albert_id == "JOB999"
    # Ensure S3 /files/sign was NOT called
    assert not any(
        "/files/sign" in call.args[0] for call in session.post.call_args_list if call.args
    )
    # Ensure worker job was posted with metadata having NO s3Url
    worker_job_calls = [
        call
        for call in session.post.call_args_list
        if call.args and "/api/v3/worker-jobs" in call.args[0]
    ]
    assert len(worker_job_calls) == 1
    metadata_sent = worker_job_calls[0].kwargs["json"]["metadata"]
    assert "s3Url" not in metadata_sent
    assert metadata_sent["albertId"] == "TASFOR1"
    assert metadata_sent["blockId"] == "BLK1"
    assert metadata_sent["newWorkflowId"] == "WFL10"


def test_generate_block_combinations_prefers_first_workflow_when_categories_unset():
    """Test that FINAL-before-INITIAL blocks use the first workflow before categories are set."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    prop_task = PropertyTask(
        id="TASFOR1",
        name="Property Task",
        blocks=[
            Block(
                id="BLK1",
                data_template=[{"id": "DAT1"}],
                workflow=[{"id": "WFL20"}, {"id": "WFL21"}],
            )
        ],
    )
    tasks_collection.get_by_id = MagicMock(return_value=prop_task)  # type: ignore[method-assign]

    wfl_resp = MagicMock()
    wfl_resp.json.return_value = {
        "id": "WFL20",
        "name": "Interval Workflow",
        "ParameterGroups": [],
    }
    session.get.return_value = wfl_resp

    tasks_collection.get_block_rules = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(rules=[], overrides=[])
    )

    job_post_resp = MagicMock()
    job_post_resp.json.return_value = {
        "albertId": "JOB777",
        "jobType": "createChildWorkflows",
        "state": "successful",
        "metadata": {
            "parentType": "TAS",
            "albertId": "TASFOR1",
            "blockId": "BLK1",
            "newWorkflowId": "WFL20",
        },
    }
    session.post.return_value = job_post_resp

    tasks_collection.generate_block_combinations(task_id="TASFOR1", block_id="BLK1", wait=False)

    session.get.assert_called_once_with("/api/v3/workflows/WFL20")


def test_generate_block_combinations_intervalized_uploads_and_submits_s3_url(monkeypatch):
    """Test that intervalized blocks generate combinations, upload to S3, and pass s3Url."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    prop_task = PropertyTask(
        id="TASFOR1",
        name="Property Task",
        blocks=[Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL20"}])],
    )
    tasks_collection.get_by_id = MagicMock(return_value=prop_task)  # type: ignore[method-assign]

    # Workflow with intervalized parameters
    wfl_resp = MagicMock()
    wfl_resp.json.return_value = {
        "albertId": "WFL20",
        "name": "Interval Workflow",
        "ParameterGroups": [
            {
                "id": "PRG1",
                "rowId": "ROW1",
                "Parameters": [
                    {
                        "id": "PRM1",
                        "shortName": "Temp",
                        "rowId": "ROW1",
                        "Intervals": [
                            {"rowId": "ROW1", "value": "20"},
                            {"rowId": "ROW2", "value": "30"},
                        ],
                    }
                ],
            }
        ],
    }
    session.get.return_value = wfl_resp

    tasks_collection.get_block_rules = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(rules=[], overrides=[])
    )

    # Sign response
    sign_resp = MagicMock()
    sign_resp.json.return_value = [{"URL": "https://s3.amazonaws.com/test-bucket/signed-url"}]
    # Worker job response
    job_post_resp = MagicMock()
    job_post_resp.json.return_value = {
        "albertId": "JOB888",
        "jobType": "createChildWorkflows",
        "state": "successful",
        "metadata": {
            "parentType": "TAS",
            "albertId": "TASFOR1",
            "blockId": "BLK1",
            "newWorkflowId": "WFL20",
            "s3Url": "intervalcombinations/TASFOR1/BLK1/test.json",
        },
    }

    def mock_post(url, *args, **kwargs):
        if "/files/sign" in url:
            return sign_resp
        if "/worker-jobs" in url:
            return job_post_resp
        return MagicMock()

    session.post.side_effect = mock_post

    mock_requests_put = MagicMock()
    mock_requests_put.return_value.status_code = 200
    monkeypatch.setattr("albert.collections.tasks.requests.put", mock_requests_put)

    job = tasks_collection.generate_block_combinations(
        task_id="TASFOR1", block_id="BLK1", wait=False
    )

    assert job.albert_id == "JOB888"
    assert mock_requests_put.called
    assert "https://s3.amazonaws.com/test-bucket/signed-url" in mock_requests_put.call_args[0]


def test_create_with_combinations_multi_block_gap_and_rules(monkeypatch):
    """Test that create_with_combinations saves rules and generates combinations for blocks."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    # Task with two blocks, each with rules
    input_task = PropertyTask(
        name="Two Block Task",
        parent_id="PRO1",
        blocks=[
            Block(
                data_template=[{"id": "DAT1"}],
                workflow=[{"id": "WFL1"}],
                rules=[
                    ExclusionRule(
                        name="Rule 1",
                        conditions=[
                            RuleCondition(
                                parameter_group_id="PRG1",
                                parameter_id="PRM1",
                                operator=RuleOperator.GT,
                                value=50,
                            )
                        ],
                    )
                ],
            ),
            Block(
                data_template=[{"id": "DAT2"}],
                workflow=[{"id": "WFL2"}],
            ),
        ],
    )

    created_task_mock = PropertyTask(
        id="TASFOR99",
        name="Two Block Task",
        parent_id="PRO1",
        blocks=[
            Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL1"}]),
            Block(id="BLK2", data_template=[{"id": "DAT2"}], workflow=[{"id": "WFL2"}]),
        ],
    )
    tasks_collection.create = MagicMock(return_value=created_task_mock)  # type: ignore[method-assign]
    tasks_collection.get_by_id = MagicMock(return_value=created_task_mock)  # type: ignore[method-assign]

    mock_generate = MagicMock()
    job1 = WorkerJob(
        albert_id="JOB1",
        job_type="createChildWorkflows",
        state=WorkerJobState.SUCCESSFUL,
        metadata={"parentType": "TAS", "albertId": "TASFOR99"},
    )
    job2 = WorkerJob(
        albert_id="JOB2",
        job_type="createChildWorkflows",
        state=WorkerJobState.SUCCESSFUL,
        metadata={"parentType": "TAS", "albertId": "TASFOR99"},
    )
    mock_generate.side_effect = [job1, job2]
    tasks_collection.generate_block_combinations = mock_generate  # type: ignore[method-assign]

    # Mock time.sleep to verify 10-second spacing
    sleep_calls = []
    current_time = [100.0]

    def fake_sleep(s):
        sleep_calls.append(s)
        current_time[0] += s

    monkeypatch.setattr("albert.collections.tasks.time.sleep", fake_sleep)
    monkeypatch.setattr("albert.collections.tasks.time.time", lambda: current_time[0])

    # Mock poll_worker_job to return successful
    monkeypatch.setattr(
        "albert.collections.tasks.poll_worker_job",
        lambda *args, **kwargs: WorkerJob(
            albert_id=kwargs.get("job_id", "JOB1"),
            job_type="createChildWorkflows",
            state=WorkerJobState.SUCCESSFUL,
            metadata=WorkerJobMetadata(parent_type="TAS", albert_id="TASFOR99"),
        ),
    )

    res = tasks_collection.create_with_combinations(task=input_task, wait=True)

    assert res.id == "TASFOR99"
    # PUT /tasks/{id}/rules was called once
    assert any(
        "/api/v3/tasks/TASFOR99/rules" in call.args[0] for call in session.put.call_args_list
    )
    # generate_block_combinations was called for both blocks
    assert mock_generate.call_count == 2
    # Sleep was called with 10.0 between the two blocks
    assert sleep_calls == [10.0]


def test_create_with_combinations_raises_error_on_failed_block(monkeypatch):
    """Test that create_with_combinations raises CombinationGenerationError on block failure."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    input_task = PropertyTask(
        name="Task with Failing Block",
        parent_id="PRO1",
        blocks=[
            Block(data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL1"}]),
            Block(data_template=[{"id": "DAT2"}], workflow=[{"id": "WFL2"}]),
        ],
    )

    created_task_mock = PropertyTask(
        id="TASFOR100",
        name="Task with Failing Block",
        parent_id="PRO1",
        blocks=[
            Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL1"}]),
            Block(id="BLK2", data_template=[{"id": "DAT2"}], workflow=[{"id": "WFL2"}]),
        ],
    )
    tasks_collection.create = MagicMock(return_value=created_task_mock)  # type: ignore[method-assign]
    tasks_collection.get_by_id = MagicMock(return_value=created_task_mock)  # type: ignore[method-assign]

    job1 = WorkerJob(
        albert_id="JOB1",
        job_type="createChildWorkflows",
        state=WorkerJobState.SUCCESSFUL,
        metadata={"parentType": "TAS", "albertId": "TASFOR100"},
    )
    job2 = WorkerJob(
        albert_id="JOB2",
        job_type="createChildWorkflows",
        state=WorkerJobState.FAILED,
        metadata={"parentType": "TAS", "albertId": "TASFOR100"},
    )
    tasks_collection.generate_block_combinations = MagicMock(side_effect=[job1, job2])  # type: ignore[method-assign]

    monkeypatch.setattr("albert.collections.tasks.time.sleep", lambda s: None)
    monkeypatch.setattr("albert.collections.tasks.time.time", lambda: 100.0)

    # Mock poll_worker_job to return job1 successful and job2 failed
    def mock_poll(*args, **kwargs):
        job_id = kwargs.get("job_id")
        if job_id == "JOB1":
            return job1
        return job2

    monkeypatch.setattr("albert.collections.tasks.poll_worker_job", mock_poll)

    with pytest.raises(CombinationGenerationError) as exc_info:
        tasks_collection.create_with_combinations(task=input_task, wait=True)

    err = exc_info.value
    assert err.task.id == "TASFOR100"
    assert err.failed_blocks == ["BLK2"]
    assert err.job_states["BLK1"] == "successful"
    assert err.job_states["BLK2"] == "failed"


def test_set_block_rules_automatically_calls_generate_block_combinations():
    """Test that set_block_rules automatically regenerates combinations and attaches job."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    # Mock PUT /tasks/TASFOR1/rules
    put_resp = MagicMock()
    put_resp.json.return_value = [
        {
            "blockId": "BLK1",
            "rules": [
                {
                    "conditions": [
                        {
                            "prgId": "PRG1",
                            "prmId": "PRM1",
                            "rowId": "ROW1",
                            "operator": "gte",
                            "value": "90",
                        }
                    ]
                }
            ],
            "overrides": [],
        }
    ]
    session.put.return_value = put_resp

    # Mock get_by_id to resolve block workflow
    prop_task = PropertyTask(
        id="TASFOR1",
        name="Property Task",
        blocks=[Block(id="BLK1", data_template=[{"id": "DAT1"}], workflow=[{"id": "WFL99"}])],
    )
    tasks_collection.get_by_id = MagicMock(return_value=prop_task)  # type: ignore[method-assign]

    mock_job = WorkerJob(
        albert_id="JOB555",
        job_type="createChildWorkflows",
        state=WorkerJobState.SUCCESSFUL,
        metadata={"parentType": "TAS", "albertId": "TASFOR1", "blockId": "BLK1"},
    )
    tasks_collection.generate_block_combinations = MagicMock(return_value=mock_job)  # type: ignore[method-assign]

    rule = ExclusionRule(
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                row_id="ROW1",
                operator=RuleOperator.GTE,
                value="90",
            )
        ]
    )

    block_rules = tasks_collection.set_block_rules(
        task_id="TASFOR1",
        block_id="BLK1",
        rules=[rule],
    )

    # Verify rules were saved via PUT
    session.put.assert_called_once()
    assert "/TASFOR1/rules" in session.put.call_args[0][0]

    # Verify generate_block_combinations was called automatically
    tasks_collection.generate_block_combinations.assert_called_once_with(
        task_id="TASFOR1",
        block_id="BLK1",
        old_workflow_id="WFL99",
        wait=True,
    )

    # Verify job is attached to the returned BlockRules
    assert block_rules.job is mock_job
    assert block_rules.job.albert_id == "JOB555"
    assert block_rules.job.state == WorkerJobState.SUCCESSFUL


def test_set_block_rules_with_generate_combinations_false_skips_generation():
    """Test that set_block_rules skips generation when generate_combinations=False."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    put_resp = MagicMock()
    put_resp.json.return_value = [{"blockId": "BLK1", "rules": [], "overrides": []}]
    session.put.return_value = put_resp

    tasks_collection.generate_block_combinations = MagicMock()  # type: ignore[method-assign]
    tasks_collection.get_by_id = MagicMock()  # type: ignore[method-assign]

    block_rules = tasks_collection.set_block_rules(
        task_id="TASFOR1",
        block_id="BLK1",
        rules=[],
        generate_combinations=False,
    )

    # Verify generate_block_combinations was NOT called
    tasks_collection.generate_block_combinations.assert_not_called()
    tasks_collection.get_by_id.assert_not_called()
    assert block_rules.job is None


def test_set_block_rules_with_custom_old_workflow_id_and_wait_false():
    """Test that set_block_rules honors explicit old_workflow_id and wait=False."""
    session = MagicMock()
    tasks_collection = TaskCollection(session=session)

    put_resp = MagicMock()
    put_resp.json.return_value = [{"blockId": "BLK1", "rules": [], "overrides": []}]
    session.put.return_value = put_resp

    mock_job = WorkerJob(
        albert_id="JOB666",
        job_type="createChildWorkflows",
        state=WorkerJobState.SUBMITTED,
        metadata={"parentType": "TAS", "albertId": "TASFOR1", "blockId": "BLK1"},
    )
    tasks_collection.generate_block_combinations = MagicMock(return_value=mock_job)  # type: ignore[method-assign]

    block_rules = tasks_collection.set_block_rules(
        task_id="TASFOR1",
        block_id="BLK1",
        rules=[],
        old_workflow_id="WFL_PREVIOUS",
        wait=False,
    )

    tasks_collection.generate_block_combinations.assert_called_once_with(
        task_id="TASFOR1",
        block_id="BLK1",
        old_workflow_id="WFL_PREVIOUS",
        wait=False,
    )
    assert block_rules.job is mock_job
    assert block_rules.job.albert_id == "JOB666"
