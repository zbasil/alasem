"""Zahraa's Supercomputer (حاسوب زهراء الخارق) - a La Liga forecasting model.

Pipeline:
    data  ->  Dixon-Coles team ratings (goals + shots-on-target + market odds)
          ->  match probabilities  ->  Monte Carlo season simulation
          ->  title / Champions League / relegation probabilities
"""

__version__ = "1.0.0"
