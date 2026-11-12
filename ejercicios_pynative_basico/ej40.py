class Car:
    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year

    def start_engine(self):
        print(f"The engine of the {self.year} {self.make} {self.model} is starting.")


# Create an instance of the Car class
my_car = Car("Toyota", "Camry", 2022)

# Call the start_engine method
my_car.start_engine()