import logging
import sys
import unittest

import sqlacodegen.generators
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import registry, Session, clear_mappers

import ormatic
import classes.example_classes as ex
from ormatic.ormatic import ORMatic
from ormatic.utils import classes_of_module, recursive_subclasses


class ORMaticTestCase(unittest.TestCase):
    session: Session
    mapper_registry: registry

    def setUp(self):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        ormatic.ormatic.logger.addHandler(handler)
        ormatic.ormatic.logger.setLevel(logging.INFO)

        self.mapper_registry = registry()
        self.engine = create_engine('sqlite:///:memory:')
        self.session = Session(self.engine)

    def tearDown(self):
        self.mapper_registry.metadata.drop_all(self.session.bind)
        clear_mappers()
        self.session.close()

    def test_no_dependencies(self):
        classes = [ex.Position, ex.Orientation]
        result = ORMatic(classes, self.mapper_registry)

        self.assertEqual(len(result.class_dict), 2)
        position_table = result.class_dict[ex.Position].mapped_table
        orientation_table = result.class_dict[ex.Orientation].mapped_table

        self.assertEqual(len(position_table.columns), 4)
        self.assertEqual(len(orientation_table.columns), 5)

        orientation_colum = [c for c in orientation_table.columns if c.name == 'w'][0]
        self.assertTrue(orientation_colum.nullable)

        p1 = ex.Position(x=1, y=2, z=3)
        o1 = ex.Orientation(x=1, y=2, z=3, w=None)

        # create all tables
        self.mapper_registry.metadata.create_all(self.session.bind)
        self.session.add(o1)
        self.session.add(p1)
        self.session.commit()

        # test the content of the database
        queried_p1 = self.session.scalars(select(ex.Position)).one()
        queried_o1 = self.session.scalars(select(ex.Orientation)).one()
        self.assertEqual(queried_p1, p1)
        self.assertEqual(queried_o1, o1)

    def test_enum_parse(self):
        classes = [ex.EnumContainer]
        result = ORMatic(classes, self.mapper_registry)
        result.make_all_tables()

        enum_container_table = result.class_dict[ex.EnumContainer].mapped_table.local_table

        self.assertEqual(len(enum_container_table.columns), 2)
        self.assertEqual(len(enum_container_table.foreign_keys), 0)

        self.mapper_registry.metadata.create_all(self.session.bind)

        enum_container = ex.EnumContainer(value=ex.ValueEnum.A)
        self.session.add(enum_container)
        self.session.commit()

        queried_enum_container = self.session.scalars(select(ex.EnumContainer)).one()
        self.assertEqual(queried_enum_container, enum_container)

    def test_one_to_one_relationships(self):
        classes = [ex.Position, ex.Orientation, ex.Pose]
        result = ORMatic(classes, self.mapper_registry)
        all_tables = result.make_all_tables()
        pose_table = result.class_dict[ex.Pose].mapped_table.local_table

        # get foreign keys of pose_table
        foreign_keys = pose_table.foreign_keys
        self.assertEqual(len(foreign_keys), 2)

        p1 = ex.Position(x=1, y=2, z=3)
        o1 = ex.Orientation(x=1, y=2, z=3, w=1)
        pose1 = ex.Pose(p1, o1)

        # create all tables
        self.mapper_registry.metadata.create_all(self.session.bind)
        self.session.add(pose1)
        self.session.commit()

        # test the content of the database
        queried_p1 = self.session.scalars(select(ex.Position)).one()
        queried_o1 = self.session.scalars(select(ex.Orientation)).one()
        queried_pose1 = self.session.scalars(select(ex.Pose)).one()
        self.assertEqual(queried_p1, p1)
        self.assertEqual(queried_o1, o1)
        self.assertEqual(queried_pose1, pose1)

    def test_one_to_many(self):
        classes = [ex.Position, ex.Positions]
        result = ORMatic(classes, self.mapper_registry)
        result.make_all_tables()

        positions_table = result.class_dict[ex.Positions].mapped_table.local_table
        position_table = result.class_dict[ex.Position].mapped_table.local_table

        foreign_keys = position_table.foreign_keys
        self.assertEqual(len(foreign_keys), 1)

        self.assertEqual(len(positions_table.columns), 2)

        self.mapper_registry.metadata.create_all(self.session.bind)

        p1 = ex.Position(x=1, y=2, z=3)
        p2 = ex.Position(x=2, y=3, z=4)

        positions = ex.Positions([p1, p2], ["a", "b"])

        self.session.add(positions)
        self.session.commit()

        positions = self.session.scalars(select(ex.Positions)).one()
        self.assertEqual(positions.positions, [p1, p2])

    def test_one_to_many_multiple(self):
        classes = [ex.Position, ex.DoublePositionAggregator]
        result = ORMatic(classes, self.mapper_registry)

        double_positions_table = result.class_dict[ex.DoublePositionAggregator].mapped_table.local_table
        position_table = result.class_dict[ex.Position].mapped_table.local_table

        foreign_keys = position_table.foreign_keys
        self.assertEqual(len(foreign_keys), 2)

        self.assertEqual(len(double_positions_table.columns), 1)

        self.mapper_registry.metadata.create_all(self.session.bind)

        p1 = ex.Position(x=1, y=2, z=3)
        p2 = ex.Position(x=2, y=3, z=4)
        p3 = ex.Position(x=3, y=4, z=5)

        positions = ex.DoublePositionAggregator([p1, p2], [p3])

        self.session.add(positions)
        self.session.commit()

        queried = self.session.scalars(select(ex.DoublePositionAggregator)).one()
        self.assertEqual(positions, queried)

    def test_inheritance(self):
        classes = [ex.Position, ex.Position4D, ex.Position5D]
        result = ORMatic(classes, self.mapper_registry)
        result.make_all_tables()

        position4d_table = result.class_dict[ex.Position4D].mapped_table.local_table

        foreign_keys = position4d_table.foreign_keys
        print(position4d_table.columns)
        print(foreign_keys)
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(len(position4d_table.columns), 2)

        # assert position table polymorphic identity
        self.mapper_registry.metadata.create_all(self.session.bind)
        # p1 = ex.Position(x=1, y=2, z=3)
        p2 = ex.Position4D(x=2, y=3, z=4, w=2)

        self.session.add_all([p2])
        self.session.commit()

        queried_p1 = self.session.scalars(select(ex.Position)).all()
        print(queried_p1)
        # self.assertEqual(queried_p1, [p1, p2])
        queried_p2 = self.session.scalars(select(ex.Position4D)).first()
        self.assertIsInstance(queried_p2, ex.Position)

    def test_tree_structure(self):
        classes = [ex.Node]
        result = ORMatic(classes, self.mapper_registry)
        result.make_all_tables()

        self.mapper_registry.metadata.create_all(self.session.bind)

        n1 = ex.Node()
        n2 = ex.Node(parent=n1)
        n3 = ex.Node(parent=n1)

        self.session.add_all([n1, n2, n3])
        self.session.commit()

        results = self.session.scalars(select(ex.Node)).all()
        n1, n2, n3 = results
        self.assertIsNone(n1.parent)
        self.assertEqual(n2.parent, n1)
        self.assertEqual(n3.parent, n1)

    def test_all_together(self):
        classes = [ex.Position, ex.Orientation, ex.Pose, ex.Position4D, ex.Positions, ex.EnumContainer]
        result = ORMatic(classes, self.mapper_registry)
        result.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

    def test_to_python_file(self):
        classes = classes_of_module(ex)

        ignore_classes = {ex.PhysicalObject, ex.PhysicalObjectType} | set(recursive_subclasses(ex.PhysicalObject))
        ignore_classes |= {cls.explicit_mapping for cls in recursive_subclasses(ex.ORMaticExplicitMapping)}
        ignore_classes |= {ex.OriginalSimulatedObject}
        ignore_classes |= set(recursive_subclasses(ex.Enum))
        ignore_classes |= {ex.Parent1, ex.Parent2, ex.MultipleInheritance}

        classes = list(set(classes) - ignore_classes)

        ormatic = ORMatic(classes, self.mapper_registry, {ex.PhysicalObject: ex.PhysicalObjectType()})
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        generator = sqlacodegen.generators.TablesGenerator(self.mapper_registry.metadata, self.session.bind, [])

        with open('orm_interface.py', 'w') as f:
            ormatic.to_python_file(generator, f)

    def test_molecule(self):
        classes = [ex.Atom, ex.Bond, ex.Molecule]
        ormatic = ORMatic(classes, self.mapper_registry)
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        atom = ex.Atom(ex.Element.I, 1, 1.0)
        bond = ex.Bond(atom, atom, 1)
        molecule = ex.Molecule(1, 1, 1.0, 1.0, True, [atom], [bond])
        self.session.add_all([atom, bond, molecule])
        self.session.commit()

        result = self.session.scalars(select(ex.Molecule).join(ex.Atom).where(ex.Atom.element == ex.Element.I).distinct()).first()
        self.assertEqual(result, molecule)
        self.assertEqual(result.color, 'red')

    def test_explicit_mappings(self):
        classes = [ex.PartialPosition]
        ormatic = ORMatic(classes, self.mapper_registry)
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        p1 = ex.Position4D(x=1, y=2, z=0, w=0)
        p2 = ex.Position4D(x=2, y=3, z=0, w=0)
        self.session.add_all([p1, p2])
        self.session.commit()

        result = self.session.scalars(select(ex.Position4D)).all()
        self.assertEqual(len(result), len([p1, p2]))
        self.assertEqual(result, [p1, p2])

    def test_type_casting(self):
        classes = [ex.Position, ex.Orientation, ex.Pose, ex.SimulatedObject]
        ormatic = ORMatic(classes, self.mapper_registry, type_mappings={ex.PhysicalObject: ex.PhysicalObjectType()})
        ormatic.make_all_tables()

        self.mapper_registry.metadata.create_all(self.session.bind)

        obj1 = ex.OriginalSimulatedObject(ex.Bowl(), ex.Pose(ex.Position(0, 0, 0), ex.Orientation(0, 0, 0, 1)), 5)
        self.session.add(obj1)
        self.session.commit()
        result = self.session.scalar(select(ex.OriginalSimulatedObject))

        self.assertEqual(result, obj1)
        self.assertIsInstance(result.concept, ex.Bowl)
        self.assertEqual(result.concept, obj1.concept)
        self.assertEqual(result.concept, obj1.concept)

        with self.session.bind.connect() as connection:
            result = connection.execute(
                text("select * from OriginalSimulatedObject JOIN Pose ON OriginalSimulatedObject.pose_id = Pose.id"))
            store_rows = []
            for row in result:
                store_rows.append(row)

        self.assertEqual(len(store_rows[0]), 6)
        self.assertEqual(type(store_rows[0][1]), str)

    def test_type_type(self):
        classes = [ex.PositionTypeWrapper]
        ormatic = ORMatic(classes, self.mapper_registry)
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        wrapper = ex.PositionTypeWrapper(ex.Position)
        self.session.add(wrapper)
        self.session.commit()
        result = self.session.scalars(select(ex.PositionTypeWrapper)).one()
        self.assertEqual(result, wrapper)

    def test_explicit_mapping_reference(self):
        classes = [ex.ObjectAnnotation, ex.SimulatedObject, ex.Pose, ex.Position, ex.Orientation]
        ormatic = ORMatic(classes, self.mapper_registry, type_mappings={ex.PhysicalObject: ex.PhysicalObjectType()})
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        og_sim = ex.OriginalSimulatedObject(ex.Bowl(), ex.Pose(ex.Position(0, 0, 0), ex.Orientation(0, 0, 0, 1)), 5.)
        object_annotation = ex.ObjectAnnotation(og_sim)
        self.session.add(object_annotation)
        self.session.commit()

        queried_annotation = self.session.scalars(select(ex.ObjectAnnotation)).one()
        self.assertEqual(queried_annotation, object_annotation)


    def test_multiple_inheritance1(self):
        classes = [ex.Parent1, ex.Parent2, ex.MultipleInheritance]
        ormatic = ORMatic(classes, self.mapper_registry)
        ormatic.make_all_tables()
        self.mapper_registry.metadata.create_all(self.session.bind)

        generator = sqlacodegen.generators.TablesGenerator(self.mapper_registry.metadata, self.session.bind, [])

        with open('orm_interface.py', 'w') as f:
            ormatic.to_python_file(generator, f)
        # print(ormatic.class_dict.keys())
        # mi_table = ormatic.class_dict[MultipleInheritance].mapped_table.local_table
        #
        # self.assertEqual(len(mi_table.columns), 2)

        mi1 = ex.MultipleInheritance("obj", "obj2", 1)
        print(mi1)
        self.session.add(mi1)
        self.session.commit()

        r1 = self.session.scalars(select(ex.MultipleInheritance)).one()
        print("r1", r1)

        r2 = self.session.scalars(select(ex.Parent1)).all()
        print("r2", r2)
        r3 = self.session.scalars(select(ex.Parent2)).all()
        print("r3", r3)

        self.assertEqual(r1, mi1)  # +1 for polymorphic_type

if __name__ == '__main__':
    unittest.main()
