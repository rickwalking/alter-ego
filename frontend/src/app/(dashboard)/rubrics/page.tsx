"use client";

import { useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Textarea,
  Badge,
  Alert,
  AlertDescription,
  Spinner,
} from "@/components/ui";
import { useRubrics } from "@/features/rubrics/hooks/use-rubrics";
import type { QualityRubric, QualityRubricCreatePayload, RubricCriterion } from "@/features/rubrics/types";

export default function RubricsPage() {
  const { rubrics, loading, error, refetch, create, update, delete: deleteRubric } = useRubrics();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<QualityRubricCreatePayload>({
    name: "",
    description: "",
    criteria: [],
    applicable_content_types: ["blog_post"],
    is_default: false,
  });
  const [criterionForm, setCriterionForm] = useState<RubricCriterion>({
    id: "",
    name: "",
    description: "",
    weight: 0.25,
    evaluation_method: "ai_auto",
    min_threshold: 0.7,
    scoring_scale: "0-100",
    prompt_template: "",
  });

  const handleCreate = async () => {
    try {
      await create(formData);
      setIsCreating(false);
      resetForm();
    } catch (err) {
      console.error("Failed to create rubric:", err);
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await update(id, formData);
      setEditingId(null);
      resetForm();
    } catch (err) {
      console.error("Failed to update rubric:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this rubric?")) return;
    try {
      await deleteRubric(id);
    } catch (err) {
      console.error("Failed to delete rubric:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      criteria: [],
      applicable_content_types: ["blog_post"],
      is_default: false,
    });
  };

  const startEdit = (rubric: QualityRubric) => {
    setEditingId(rubric.id);
    setFormData({
      name: rubric.name,
      description: rubric.description || "",
      criteria: rubric.criteria,
      applicable_content_types: rubric.applicable_content_types,
      is_default: rubric.is_default,
    });
  };

  const addCriterion = () => {
    if (!criterionForm.name || !criterionForm.id) return;
    setFormData({
      ...formData,
      criteria: [...(formData.criteria || []), { ...criterionForm }],
    });
    setCriterionForm({
      id: "",
      name: "",
      description: "",
      weight: 0.25,
      evaluation_method: "ai_auto",
      min_threshold: 0.7,
      scoring_scale: "0-100",
      prompt_template: "",
    });
  };

  const removeCriterion = (index: number) => {
    setFormData({
      ...formData,
      criteria: formData.criteria?.filter((_, i) => i !== index) || [],
    });
  };

  if (loading && rubrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Quality Rubrics</h1>
        <Button onClick={() => setIsCreating(true)} disabled={isCreating}>
          Create Rubric
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {(isCreating || editingId) && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>{editingId ? "Edit Rubric" : "Create New Rubric"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Name</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Blog Post Quality Standards"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe what this rubric evaluates..."
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default || false}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
              />
              <label htmlFor="is_default" className="text-sm font-medium">
                Set as default rubric
              </label>
            </div>

            <div className="border-t pt-4">
              <h3 className="font-medium mb-3">Criteria</h3>
              <div className="grid gap-3 mb-4">
                {formData.criteria?.map((criterion, index) => (
                  <div key={index} className="flex items-center justify-between bg-muted p-3 rounded-md">
                    <div>
                      <span className="font-medium">{criterion.name}</span>
                      <span className="text-muted-foreground text-sm ml-2">
                        Weight: {criterion.weight}
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => removeCriterion(index)}>
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3 p-4 border rounded-md">
                <Input
                  placeholder="Criterion ID (e.g., e_at_score)"
                  value={criterionForm.id}
                  onChange={(e) => setCriterionForm({ ...criterionForm, id: e.target.value })}
                />
                <Input
                  placeholder="Criterion Name"
                  value={criterionForm.name}
                  onChange={(e) => setCriterionForm({ ...criterionForm, name: e.target.value })}
                />
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  placeholder="Weight"
                  value={criterionForm.weight}
                  onChange={(e) => setCriterionForm({ ...criterionForm, weight: parseFloat(e.target.value) })}
                />
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={criterionForm.evaluation_method}
                  onChange={(e) => setCriterionForm({ ...criterionForm, evaluation_method: e.target.value })}
                >
                  <option value="ai_auto">AI Auto</option>
                  <option value="human_required">Human Required</option>
                  <option value="hybrid">Hybrid</option>
                </select>
                <Textarea
                  placeholder="Prompt Template"
                  value={criterionForm.prompt_template}
                  onChange={(e) => setCriterionForm({ ...criterionForm, prompt_template: e.target.value })}
                  className="col-span-2"
                />
                <Button onClick={addCriterion} className="col-span-2">
                  Add Criterion
                </Button>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => {
                  if (editingId) {
                    handleUpdate(editingId);
                  } else {
                    handleCreate();
                  }
                }}
              >
                {editingId ? "Update" : "Create"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                  resetForm();
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4">
        {rubrics.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No rubrics yet. Create your first quality rubric to get started.
            </CardContent>
          </Card>
        ) : (
          rubrics.map((rubric) => (
            <Card key={rubric.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-xl">{rubric.name}</CardTitle>
                    {rubric.is_default && (
                      <Badge variant="default">Default</Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => startEdit(rubric)}>
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(rubric.id)}
                      disabled={rubric.is_default}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {rubric.description || "No description"}
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Criteria</h4>
                  <div className="grid gap-2">
                    {rubric.criteria.map((criterion: RubricCriterion) => (
                      <div
                        key={criterion.id}
                        className="flex items-center justify-between p-3 bg-muted rounded-md"
                      >
                        <div>
                          <span className="font-medium text-sm">{criterion.name}</span>
                          <span className="text-muted-foreground text-sm ml-2">
                            ({criterion.evaluation_method})
                          </span>
                        </div>
                        <Badge variant="secondary">Weight: {criterion.weight}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="text-sm text-muted-foreground">Applies to:</span>
                  {rubric.applicable_content_types.map((type: string) => (
                    <Badge key={type} variant="outline">
                      {type}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
