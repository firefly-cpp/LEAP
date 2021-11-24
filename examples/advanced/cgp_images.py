"""Example demonstrating the use of Cartesion genetic programming (CGP) to
evolve images.

Usage:
  cgp_images.py [options] [--viz | --no-viz]
  cgp_images.py -h | --help

Options:
  -h --help             Show this screen.
  --generations=<n>             Number of generations to run for. [default: 2000]
  --viz                         Show GUI visualization.
  --no-viz                      Do not show GUI visualization.
"""
import os
import sys

from docopt import docopt
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

from leap_ec.algorithm import generational_ea
from leap_ec import ops, probe, test_env_var
from leap_ec.representation import Representation
from leap_ec.executable_rep import cgp, neural_network, problems
from leap_ec.int_rep import create_int_vector
from leap_ec.real_rep.ops import genome_mutate_gaussian
from leap_ec.segmented_rep.ops import segmented_mutate


##############################
# Function best_image_probe()
##############################
def best_image_probe(width: int, height: int, ax):
    def f(population: list):
        best = max(population)
        executable = best.decode()
        img_array = problems.ImageXYProblem.generate_image(executable, width, height)
        img_array = img_array.reshape(height, width, 3)
        print(img_array)
        ax.imshow(img_array)
        plt.pause(0.000001)
        return population

    return f


##############################
# Entry Point
##############################
if __name__ == '__main__':

    ##############################
    # Parameters
    ############################## 
    # CLI Parameters
    arguments = docopt(__doc__)
    generations = int(arguments['--generations']) 
    viz = False if arguments['--no-viz'] else True

    # Fixed parameters
    pop_size = 5
    params_mutate_std = 5.0
    image_path = './examples/advanced/cgp_image_centipede_small.jpg'
    modulo = 10  # For visualization

    # When running the test harness, just run for two generations
    # (we use this to quickly ensure our examples don't get bitrot)
    if os.environ.get(test_env_var, False) == 'True':
        generations = 2


    ##############################
    # CGP components
    ##############################
    decoder = cgp.CGPWithParametersDecoder(
                    primitives=cgp.cgp_art_primitives(),
                    num_inputs = 2,
                    num_outputs = 3,
                    num_layers=10,
                    nodes_per_layer=1,
                    max_arity=2,
                    num_parameters_per_node=1
                )
    cgp_decoder = decoder.cgp_decoder


    cgp_representation = Representation(
                            decoder=decoder,
                            # We use a sepecial initializer that obeys the CGP & parameter constraints
                            initialize=decoder.initialize(
                                parameters_initializer=create_int_vector(
                                    bounds=[(0, 255)]*cgp_decoder.num_layers*cgp_decoder.nodes_per_layer)
                            )
                        )


    ##############################
    # Problem
    ##############################
    problem = problems.ImageXYProblem(image_path)


    ##############################
    # Visualization probes
    ##############################
    if viz:
        plt.figure(figsize=(15, 4))
        plt.subplot(131)
        plt.title("Target Image")
        plt.imshow(problem.img_array.reshape(problem.height, problem.width, 3))

        plt.subplot(132)
        p2 = probe.FitnessPlotProbe(modulo=modulo, ax=plt.gca())
        
        plt.subplot(133)
        plt.title("Best Image Phenotype")
        p3 = best_image_probe(problem.width, problem.height, ax=plt.gca())

        viz_probes = [ p2, p3 ]
    else:
        viz_probes = []

    
    ##############################
    # Algorithm
    ##############################
    ea = generational_ea(generations, pop_size,

            representation=cgp_representation,

            # Our fitness function will be to solve the XOR problem
            problem=problem,

            pipeline=[
                ops.tournament_selection,
                ops.clone,
                segmented_mutate(mutator_functions=[
                    cgp.cgp_genome_mutate(cgp_decoder, expected_num_mutations=1),
                    genome_mutate_gaussian(std=params_mutate_std,
                                           expected_num_mutations=1,
                                           hard_bounds=(0, 255))
                ]),
                ops.evaluate,
                ops.pool(size=pop_size),
                probe.FitnessStatsCSVProbe(stream=sys.stdout)
            ] + viz_probes
    )

    list(ea)

