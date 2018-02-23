from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from src.classifiers.utils import check_is_fitted
from src.utils import get_labels_np_array


class AdversarialTrainer:
    """
    Class performing adversarial training based on a model architecture and one or multiple attack methods.
    """
    # TODO Define a data augmentation procedure; for now, all attacks are applied to all data instances.
    def __init__(self, classifier, attacks):
        """
        Create an AdversarialTrainer instance.

        :param classifier: (Classifier) model to train adversarially
        :param attacks: (Attack or list(Attack) or dict(Attack: dict(string: sequence)))
            {fgsm: {'eps': .1, 'clip_min': 0}, 'deepfool': {...}}
        """
        # TODO add Sequence support for attack parameters
        self.classifier = classifier
        if not isinstance(attacks, (list, dict)):
            attacks = {attacks: {}}
        elif isinstance(attacks, list):
            attacks = {a: {} for a in attacks}
        self.attacks = attacks

    def fit(self, x_val, y_val, **kwargs):
        """
        Train a model adversarially. Each attack specified when creating the AdversarialTrainer is applied to all
        samples in the dataset, and only the successful ones (on the source model) are kept for data augmentation.

        :param x_val: (np.ndarray) Training set
        :param y_val: (np.ndarray) Labels
        :param kwargs: (dict) Dictionary of parameters to be passed on to the fit method of the classifier
        :return: None
        """
        x_augmented = list(x_val.copy())
        y_augmented = list(y_val.copy())

        # Generate adversarial samples for each attack
        for i, attack in enumerate(self.attacks):
            # Fit the classifier to be used for the attack if needed
            if hasattr(attack.classifier, 'is_fitted'):
                if not attack.classifier.is_fitted:
                    attack.classifier.fit(x_val, y_val, **kwargs)
            else:
                attack.classifier.fit(x_val, y_val, **kwargs)

            # Predict new labels for the adversarial samples generated
            x_adv = attack.generate(x_val, **self.attacks[attack])
            y_pred = get_labels_np_array(attack.classifier.predict(x_adv))
            x_adv = x_adv[np.argmax(y_pred, axis=1) != np.argmax(y_val, axis=1)]
            y_adv = y_pred[np.argmax(y_pred, axis=1) != np.argmax(y_val, axis=1)]

            # Only add successful attacks to augmented dataset
            x_augmented.extend(list(x_adv))
            y_augmented.extend(list(y_adv))

        # Fit the model with the extended dataset
        self.classifier.fit(np.array(x_augmented), np.array(y_augmented), **kwargs)
        self.x = x_augmented
        self.y = y_augmented

    def predict(self, x_val, **kwargs):
        """
        Perform prediction using the adversarially trained classifier.

        :param x_val: Test set
        :param kwargs: Other parameters
        :return: Predictions for test set
        """
        if check_is_fitted(self, ['x', 'y']):
            return self.classifier.predict(x_val, **kwargs)
