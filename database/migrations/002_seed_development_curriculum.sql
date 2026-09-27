ALTER TABLE concepts ADD COLUMN description TEXT NOT NULL DEFAULT '';
ALTER TABLE concepts ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 1;

INSERT OR IGNORE INTO topics (id, title, description, sequence_order)
VALUES (
    'top_decision_trees',
    'Decision Trees Fundamentals',
    'Learn how decision trees make predictions by splitting data into increasingly focused groups.',
    100
);

INSERT OR IGNORE INTO concepts (id, topic_id, title, description, base_difficulty, sequence_order)
VALUES
    (
        'cpt_entropy',
        'top_decision_trees',
        'Entropy',
        'Measure how mixed or uncertain the class labels in a dataset are.',
        1,
        1
    ),
    (
        'cpt_information_gain',
        'top_decision_trees',
        'Information Gain',
        'Measure how much a split reduces the uncertainty in a dataset.',
        2,
        2
    ),
    (
        'cpt_tree_splits',
        'top_decision_trees',
        'Choosing a Tree Split',
        'Compare candidate features and choose a split that best separates the data.',
        3,
        3
    );
