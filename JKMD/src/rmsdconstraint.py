def compare_pair(arg):
    from ArbAlign import compare
    from ase.io import read
    REF = read('/home/kubeckaj/TEST/REACTIVE_MD/ref.xyz')
    return compare(REF,arg)

def numerical_derivative(func, atoms, epsilon=1e-2):
    """
    Compute numerical derivatives using finite differences.
    :param func: Function that takes atoms and returns a scalar (e.g., RMSD)
    :param positions: np.ndarray of shape (N, 3), atomic positions
    :param epsilon: Small step for finite differences
    :return: np.ndarray of shape (N, 3), numerical gradient
    """
    import numpy as np
    gradient = np.zeros_like(atoms.get_positions())
    here = func(atoms)
    for i in range(len(gradient)):  # Loop over atoms
        for j in range(3):  # Loop over x, y, z coordinates
            atoms_forward = atoms.copy()
            positions_forward = atoms.get_positions()
            positions_forward[i, j] += epsilon
            atoms_forward.set_positions(positions_forward)
            gradient[i, j] = (func(atoms_forward) - here) / epsilon
    return gradient

class RMSDConstraint:
    """Constrain an atom to move along a given direction only."""
    def __init__(self, a, k, r, adjuststeps = 0):
        self.delay_step = 0
        self.a = a
        self.k = k*0.043364115308770496
        self.r = r
        self.remembered_forces = None
        self.step = 0
        self.adjusthalf = 0
        self.adjuststeps = adjuststeps
        if self.adjuststeps > 0:
          self.k_to_be = self.k
          self.k = self.k_to_be * self.step / self.adjuststeps
    def adjust_positions(self, atoms, newpositions):
        pass
    def adjust_potential_energy(self, atoms):
        import numpy as np
        CS = atoms.constraints
        #print(CS)
        del atoms.constraints
        rmsd = compare_pair(atoms)
        #TODO: testing some stupid adjustment
        bias_en = 0.5*self.k*(rmsd-self.r-rmsd/(self.step+1)**0.5)**2
        print("RMSD: " + str(compare_pair(atoms)) + " Bias energy: " + str(bias_en * 23.0609) + " kcal/mol")
        #print(bias_en)
        atoms.set_constraint(CS)
        return 0*bias_en
    def adjust_forces(self, atoms, forces):
        import numpy as np
        if self.delay_step == 0:
          CS = atoms.constraints
          del atoms.constraints
          adjustment = self.k*numerical_derivative(compare_pair, atoms)
          #print(adjustment)
          maximum = 2*np.max(np.abs(forces))
          adjustment[adjustment > maximum] = maximum
          adjustment[adjustment < -maximum] = -maximum
          forces -= adjustment
          atoms.set_constraint(CS)
          #print(forces[0])
          #print("-----")
          if self.adjuststeps > self.step:
            if self.adjusthalf == 0:
              self.adjusthalf = 1 
            else:
              self.adjusthalf = 0
              self.step += 1
              self.k = self.k_to_be * self.step / self.adjuststeps
          self.remembered_forces = adjustment
        else:
          forces -= self.remembered_forces
        if np.mod(self.delay_step, 2*1) == 0 and self.delay_step > 0:
          self.delay_step = 0
        else:
          self.delay_step += 1
    def index_shuffle(self, atoms, ind):
        pass
