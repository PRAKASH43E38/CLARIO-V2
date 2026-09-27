import json
from typing import Type, TypeVar, Optional, Dict, Any, Callable
from pydantic import BaseModel
from backend.app.ai.base import BaseAIProvider

T = TypeVar("T", bound=BaseModel)

class MockAIProvider(BaseAIProvider):
    """Deterministic AI Provider for test suites and offline development."""

    def __init__(self, custom_responses: Optional[Dict[str, Any]] = None):
        self.custom_responses = custom_responses or {}
        self.call_history = []

    def set_response_for_model(self, model_name: str, response_data: Any):
        self.custom_responses[model_name] = response_data

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        model_name = response_model.__name__
        self.call_history.append({
            "type": "structured",
            "model_name": model_name,
            "prompt": prompt,
            "system_instruction": system_instruction,
            "temperature": temperature,
        })

        if model_name in self.custom_responses:
            data = self.custom_responses[model_name]
            if isinstance(data, dict):
                return response_model(**data)
            return data

        # Provide sensible default mock data matching specific schemas
        defaults = self._generate_default_for_model(model_name, prompt)
        return response_model(**defaults)

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        self.call_history.append({
            "type": "text",
            "prompt": prompt,
            "system_instruction": system_instruction,
            "temperature": temperature,
        })
        return f"Mock text response for prompt: {prompt[:30]}..."

    def _generate_default_for_model(self, model_name: str, prompt: str = "") -> Dict[str, Any]:
        if model_name == "ResearchOutput":
            return {
                "topic": "Decision Trees",
                "overview": "Decision Trees are versatile supervised machine learning algorithms.",
                "key_concepts": [
                    {"title": "Entropy", "description": "Measurement of impurity in a dataset.", "base_difficulty": 1},
                    {"title": "Information Gain", "description": "Reduction in entropy after a dataset split.", "base_difficulty": 2}
                ],
                "examples": ["Predicting loan defaults", "Medical diagnostics"],
                "prerequisites": ["Basic Probability", "Logarithms"]
            }
        elif model_name == "TeachingOutput":
            return {
                "concept": "Entropy",
                "explanation": "Entropy represents how mixed or disordered a group of items is.",
                "step_by_step_breakdown": [
                    "Step 1: Identify the classes in the set.",
                    "Step 2: Calculate the probability of each class.",
                    "Step 3: Compute the weighted logarithm of probabilities."
                ],
                "analogy": "Imagine a bowl of candies: all red means zero entropy; mixed colors means high entropy.",
                "intuitive_example": "A coin toss with a two-headed coin has zero entropy because the outcome is certain.",
                "check_for_understanding_prompt": "If a dataset has only positive labels, what is its entropy?"
            }
        elif model_name == "MiraGeneratedTeaching":
            task_json = prompt.partition("Teaching task:\n")[2]
            task = json.loads(task_json) if task_json else {}
            concept = task.get("current_concept", {})
            level = task.get("current_level", "beginner")
            interest = task.get("interest", "an example")
            description = concept.get("description") or (
                "The supplied research package does not include enough detail "
                "for a more specific explanation."
            )
            package = task.get("shared_research_package", {})
            sources = package.get("selected_sources", [])
            return {
                "concept": concept.get("title", "Current concept"),
                "explanation": (
                    f"{description} Start with this idea, then connect each step "
                    "back to the goal you described."
                ),
                "key_points": [
                    "Begin with the concept's core idea.",
                    "Use the supplied context to connect it to the learning goal.",
                ],
                "examples": [
                    f"Consider how this concept could be used in a {interest} example."
                ],
                "learner_level": level,
                "teaching_style": "clear, step-by-step explanation",
                "source_reference_ids": [
                    sources[0]["source_id"]
                ] if sources else [],
            }
        elif model_name == "AyanGeneratedThinking":
            task_json = prompt.partition("Critical-thinking task:\n")[2]
            task = json.loads(task_json) if task_json else {}
            teaching = task.get("mira_teaching_result", {})
            references = task.get("research_source_references", [])
            level = task.get("current_level", "beginner")
            concept = task.get("concept", teaching.get("concept", "Current concept"))
            return {
                "concept": concept,
                "thinking_prompt": (
                    f"Why would {concept} be useful for the learning goal you described? "
                    "Explain how you would reason through an example."
                ),
                "expected_reasoning_focus": [
                    "Explain the connection between the concept and the stated goal.",
                    "Describe the reasoning steps rather than recalling a definition.",
                ],
                "difficulty": level,
                "source_reference_ids": [
                    references[0]["source_id"]
                ] if references else [],
            }
        elif model_name == "KiraGeneratedPractical":
            task_json = prompt.partition("Kira practical task:\n")[2]
            task = json.loads(task_json) if task_json else {}
            concept = task.get("concept_name", "the concept")
            context = task.get("learner_context", {})
            interest = context.get("interest", "a real-world setting")
            sources = task.get("research_source_ids", [])
            output = {
                "scenario": (
                    f"A learner working with {interest} needs to apply {concept} "
                    "to make a practical choice."
                ),
                "practical_task": (
                    f"Use {concept} to explain how you would approach the decision "
                    "in this scenario."
                ),
                "real_world_context": (
                    f"This models how {concept} can support a decision in {interest}."
                ),
                "expected_action": (
                    "Identify relevant information, apply the concept, and explain "
                    "the reasoning behind the chosen action."
                ),
                "success_criteria": [
                    "Connect the supplied information to the concept.",
                    "Describe a practical action and explain why it fits the scenario.",
                ],
                "difficulty": context.get("learner_level", "beginner"),
                "research_source_ids": sources[:1],
            }
            return output
        elif model_name == "ZaynGeneratedQuiz":
            task_json = prompt.partition("Zayn quiz task:\n")[2]
            task = json.loads(task_json) if task_json else {}
            concept_id = task.get("concept_id", "concept")
            concept = task.get("concept_name", "the concept")
            difficulty = task.get("difficulty", "EASY")
            questions = []
            for index in range(task.get("question_count", 5)):
                correct = f"Apply {concept} to the supplied evidence in case {index + 1}"
                questions.append({
                    "question_id": f"question_{index + 1}",
                    "question": (
                        f"Which approach best applies {concept} to the current "
                        f"learning scenario {index + 1}?"
                    ),
                    "options": [
                        correct,
                        "Ignore the evidence and choose at random",
                        "Use an unrelated concept instead",
                        "Skip the reasoning and assume an outcome",
                    ],
                    "correct_answer": correct,
                    "explanation": (
                        f"This choice applies {concept} to the supplied context "
                        "and explains the reasoning."
                    ),
                    "difficulty": difficulty,
                    "concept_id": concept_id,
                })
            return {"questions": questions, "difficulty": difficulty}
        elif model_name == "ElaraGeneratedEvaluation":
            task_json = prompt.partition("Elara evaluation task:\n")[2]
            task = json.loads(task_json) if task_json else {}
            performance = task.get("quiz_result_reference", {}).get(
                "performance", {}
            )
            accuracy = performance.get("accuracy", 0)
            strength = (
                "strong" if accuracy >= 80
                else "moderate" if accuracy >= 50
                else "weak"
            )
            weakness = "none" if strength == "strong" else "conceptual"
            signal = (
                "increase" if strength == "strong"
                else "decrease" if strength == "weak"
                else "maintain"
            )
            concept = task.get("concept_name", "the current concept")
            return {
                "concept_strength": strength,
                "concept_weakness": weakness,
                "quiz_performance": performance,
                "thinking_evidence": "unavailable",
                "practical_evidence": "unavailable",
                "overall_evaluation": (
                    f"The submitted quiz provides {strength} evidence for "
                    f"{concept}; learner thinking and practical responses are unavailable."
                ),
                "confidence": 0.65,
                "difficulty_signal": signal,
                "evidence_summary": (
                    f"Quiz accuracy is {accuracy}%; Ayan and Kira learner responses "
                    "were not collected and are excluded."
                ),
            }
        elif model_name == "CriticalThinkingQuestion":
            return {
                "question": "What happens to entropy when the distribution of classes is completely equal?",
                "probing_type": "what_if",
                "expected_reasoning_points": [
                    "Maximum uncertainty",
                    "Probability equals 0.5 for each binary class",
                    "Entropy evaluates to 1.0"
                ]
            }
        elif model_name == "CriticalThinkingAssessment":
            return {
                "reasoning_assessment": "The learner correctly linked equal distribution to maximum uncertainty.",
                "conceptual_understanding": "high",
                "misconception": None,
                "confidence": 0.95
            }
        elif model_name == "PracticalExercise":
            return {
                "scenario_title": "Credit Risk Split",
                "practical_type": "case_study",
                "scenario_description": "A bank wants to split applicants by income level.",
                "task_prompt": "Calculate whether splitting by income gives greater purity than splitting by age.",
                "hints": ["Calculate the entropy before and after the split."]
            }
        elif model_name == "QuizQuestion":
            # If prompt indicates retest (attempt > 1 or exclude q_001), provide a fresh question instance
            if "Attempt Number: 2" in prompt or "q_001" in prompt:
                return {
                    "question_id": "q_002",
                    "format": "mcq",
                    "question_text": "If a dataset is 90% positive and 10% negative, how does its entropy compare to an even 50/50 split?",
                    "options": [
                        "A. Lower entropy (less uncertainty)",
                        "B. Higher entropy (more uncertainty)",
                        "C. Exactly identical entropy",
                        "D. Zero entropy"
                    ],
                    "correct_answer": "A. Lower entropy (less uncertainty)",
                    "difficulty": 1
                }
            elif "Attempt Number: 3" in prompt or "q_002" in prompt:
                return {
                    "question_id": "q_003",
                    "format": "mcq",
                    "question_text": "Under what condition does entropy reach its theoretical maximum in a binary classification problem?",
                    "options": [
                        "A. When p = 0.5 for both classes",
                        "B. When all samples belong to one class",
                        "C. When there are no samples",
                        "D. When the feature variance is zero"
                    ],
                    "correct_answer": "A. When p = 0.5 for both classes",
                    "difficulty": 1
                }
            return {
                "question_id": "q_001",
                "format": "mcq",
                "question_text": "What does an entropy value of 0 indicate?",
                "options": [
                    "A. Pure dataset with only one class",
                    "B. 50/50 balanced dataset",
                    "C. Infinite variance",
                    "D. Undefined calculation"
                ],
                "correct_answer": "A. Pure dataset with only one class",
                "difficulty": 1
            }
        elif model_name == "QuizGrading":
            return {
                "score": 100.0,
                "concept_performance": 100.0,
                "mistakes": [],
                "difficulty": 1,
                "recommendation": "Ready to advance to Information Gain."
            }
        elif model_name == "MasterEvaluation":
            return {
                "strong_concepts": ["Entropy"],
                "weak_concepts": [],
                "misconceptions": [],
                "concept_status": {"Entropy": "mastered"},
                "remediation_required": False,
                "recommended_action": "advance"
            }
        return {}
