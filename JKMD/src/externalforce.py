class ExternalForce:

    def __init__(self, QEF, QEF_par, QEF_systems, towards_point=[0,0,0]):
        if QEF == 'h_A':
          self.qef = 'h_A'
          self.k_ext = QEF_par*0.0433634
          self.end = [0,0,0]
          self.mfrom = QEF_systems[0]
          self.mto = QEF_systems[1]
        if QEF == 'fbh_A':
          self.qef = 'fbh_A'
          self.k_ext = QEF_par[1]*0.0433634
          #towards_point = radius
          self.end = [0,0,0]
          self.r0 = QEF_par[0]
          self.mfrom = QEF_systems[0]
          self.mto = QEF_systems[1]
        if QEF == 'c_COM':
          self.qef = 'c_COM'
          self.force = np.array(QEF_par)*0.0433634
          self.mfrom = QEF_systems[0]
          self.mto = QEF_systems[1]

    def adjust_positions(self, atoms, new):
        pass

    def index_shuffle(self, atoms, ind):
        pass

    def adjust_forces(self, atoms, forces):
        CS = atoms.constraints
        del atoms.constraints
        if self.qef == 'h_A':
          import numpy as np
          vec = atoms[self.mfrom:self.mto].get_positions() - np.array([0,0,0])
          external_force = -self.k_ext*vec
        elif self.qef == 'fbh_A':
          import numpy as np
          def heaviside(x, x0=self.r0):
            return np.linalg.norm(x, axis = 1) >= x0
          com = atoms[self.mfrom:self.mto].get_center_of_mass()
          #print(com)
          vec = atoms[self.mfrom:self.mto].get_positions() - com
          #print(atoms[self.mfrom:self.mto].get_positions())
          #print(vec)
          #print(heaviside(vec).reshape(-1,1))
          #print(self.r0*vec/np.linalg.norm(vec,axis=1).reshape(-1,1))
          external_force = - self.k_ext * heaviside(vec).reshape(-1,1) * (vec - self.r0 * vec/np.linalg.norm(vec,axis=1).reshape(-1,1))
        elif self.qef == 'c_COM':
          import numpy as np
          masses = atoms[self.mfrom:self.mto].get_masses()
          external_force = np.array(masses)[:,np.newaxis]/np.sum(masses) * self.force
        forces[self.mfrom:self.mto] += external_force
        atoms.set_constraint(CS)

    def adjust_potential_energy(self, atoms):
        if self.qef == 'h_A':
          CS = atoms.constraints
          del atoms.constraints
          import numpy as np
          pos = atoms[self.mfrom:self.mto].get_positions()
          external_energy = 0.5 * np.sum(self.k_ext*np.array([np.linalg.norm(np.array([0,0,0])-i)**2 for i in pos]))
          atoms.set_constraint(CS)
          return external_energy
        if self.qef == 'fbh_A':
          CS = atoms.constraints
          del atoms.constraints
          import numpy as np
          com = atoms[self.mfrom:self.mto].get_center_of_mass()
          vec = atoms[self.mfrom:self.mto].get_positions() - com
          def heaviside(x, x0=self.r0):
            return np.linalg.norm(x, axis = 1) >= x0
          external_energy = 0.5 * self.k_ext * np.sum(heaviside(vec).reshape(-1,1) * (vec - self.r0 * vec/np.linalg.norm(vec,axis=1).reshape(-1,1))**2)
          #external_energy = 0.5 * np.sum(self.k_ext*np.array([np.linalg.norm(np.array([0,0,0])-i)**2 for i in pos]))
          atoms.set_constraint(CS)
          return external_energy
        elif self.qef == 'c_COM':
          return 0

    #def todict(self):
    #    return {'name': 'ExternalForce',
    #            'kwargs': {'a1': self.indices[0], 'a2': self.indices[1],
    #                       'f_ext': self.external_force}}
